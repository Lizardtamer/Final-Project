import { useEffect, useState } from 'react';
import { Container, Card, Form, Button, ListGroup } from 'react-bootstrap';
import './Chat.css';

const Chat = () => {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! I\'m your Memphis Booking Assistant. I can help you:\n\n1. Add a new local artist to the database\n2. Get booking recommendations for a touring artist\n\nWhat would you like to do? (Type "add" or "recommend")' }
  ]);
  const [input, setInput] = useState('');
  const [step, setStep] = useState('choose'); // 'choose', 'name', 'genre', 'confirm', 'done', 'rec-chat'
  const [artistData, setArtistData] = useState({ name: '', genre: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(null);
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8001/health');
        if (response.ok) {
          setBackendOnline(true);
          return;
        }
      } catch {
        setBackendOnline(false);
      }

      setBackendOnline(false);
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: 'Backend appears to be offline right now. Start the API at http://127.0.0.1:8001, then try again.'
      }]);
    };

    checkHealth();
  }, []);

  const handleSend = async (chipText = null) => {
    const userInput = chipText !== null ? chipText : input;
    if (!userInput.trim()) return;

    const userMessage = { sender: 'user', text: userInput };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    // Process based on current step
    if (step === 'choose') {
      if (userInput.toLowerCase().includes('add')) {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Great! What is the name of the local artist you want to add to our database?' 
        }]);
        setStep('name');
      } else if (userInput.toLowerCase().includes('rec') || userInput.toLowerCase().includes('recommend')) {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Perfect! Tell me what you\'re looking for (artist, genres, vibe, constraints).\n\nType "back" to return to the main menu or "reset" to clear chat context.' 
        }]);
        setStep('rec-chat');
      } else {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'I didn\'t understand that. Please type "add" to add an artist or "recommend" to get booking recommendations.' 
        }]);
      }
    } else if (step === 'rec-chat') {
      if (userInput.toLowerCase() === 'back') {
        setMessages(prev => [...prev, {
          sender: 'bot',
          text: 'Back to main menu. Type "add" or "recommend".'
        }]);
        setStep('choose');
        return;
      }

      const shouldReset = userInput.toLowerCase() === 'reset';
      setIsLoading(true);
      try {
        const response = await fetch('http://127.0.0.1:8001/chat_recommend', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: shouldReset ? 'Start a fresh recommendation chat.' : userInput,
            session_id: chatSessionId,
            reset_session: shouldReset,
            top_k: 7,
            candidate_pool: 15,
          })
        });
        const data = await response.json();

        if (response.ok) {
          setChatSessionId(data.session_id || null);
          const result = data.result || {};
          const recs = result.recommendations || [];

          let recText = `${data.message}\n\n`;
          recs.forEach((rec, idx) => {
            recText += `${idx + 1}. ${rec.artist}\n   Genre: ${rec.genre}\n   Why: ${rec.reason}\n\n`;
          });

          if (result.source === 'local') {
            recText += 'Note: This turn used local ranking fallback.';
          }
          
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: recText 
          }]);
        } else {
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: `Sorry, there was an error: ${data.detail}` 
          }]);
        }
      } catch {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
            text: `Error connecting to the server. Make sure the backend is running on http://127.0.0.1:8001` 
        }]);
      }
      setIsLoading(false);
    } else if (step === 'name') {
      setArtistData(prev => ({ ...prev, name: userInput }));
      setMessages(prev => [...prev, { 
        sender: 'bot', 
        text: `Great! What genre does ${userInput} perform?` 
      }]);
      setStep('genre');
    } else if (step === 'genre') {
      setArtistData(prev => ({ ...prev, genre: userInput }));
      setMessages(prev => [...prev, { 
        sender: 'bot', 
        text: `Perfect! Let me confirm:\n\nArtist: ${artistData.name}\nGenre: ${userInput}\n\nShould I add this artist to the database? (yes/no)` 
      }]);
      setStep('confirm');
    } else if (step === 'confirm') {
      if (userInput.toLowerCase().includes('yes') || userInput.toLowerCase().includes('y')) {
        setIsLoading(true);
        try {
          const response = await fetch('http://127.0.0.1:8001/add_artist', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              name: artistData.name,
              genre: artistData.genre
            })
          });

          const data = await response.json();

          if (response.ok) {
            setMessages(prev => [...prev, { 
              sender: 'bot', 
              text: `✓ ${data.message}\n\nWould you like to add another artist? (yes/no)` 
            }]);
            setStep('done');
          } else {
            setMessages(prev => [...prev, { 
              sender: 'bot', 
              text: `Sorry, there was an error: ${data.detail}` 
            }]);
          }
        } catch {
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: `Error connecting to the server. Make sure the backend is running on http://127.0.0.1:8001` 
          }]);
        }
        setIsLoading(false);
      } else {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Okay, the artist was not added. Would you like to start over? (yes/no)' 
        }]);
        setStep('done');
      }
    } else if (step === 'done') {
      if (userInput.toLowerCase().includes('yes') || userInput.toLowerCase().includes('y')) {
        setArtistData({ name: '', genre: '' });
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Great! What is the name of the artist you want to add?' 
        }]);
        setStep('name');
      } else {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Would you like to add an artist or get recommendations? (Type "add" or "recommend", or "quit" to exit)' 
        }]);
        setStep('choose');
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const handleReset = () => {
    setMessages([{
      sender: 'bot',
      text: 'Hello! I\'m your Memphis Booking Assistant. I can help you:\n\n1. Add a new local artist to the database\n2. Get booking recommendations for a touring artist\n\nWhat would you like to do? (Type "add" or "recommend")'
    }]);
    setStep('choose');
    setChatSessionId(null);
    setArtistData({ name: '', genre: '' });
    setInput('');
  };

  return (
    <div className="chat-page">
      <Container>
        <Card className="chat-card">
          <Card.Header className="chat-card-header">
            <div>
              <h4 className="chat-header-title">Book.AI</h4>
              <p className="chat-header-subtitle">Find strong local openers for your touring act</p>
            </div>
            <span className="chat-status-pill">
              <span className={`chat-status-dot ${backendOnline ? 'online' : 'offline'}`} />
              {backendOnline ? 'Online' : 'Offline'}
            </span>
          </Card.Header>
          <div className="chat-chips">
            <button className="chat-chip" onClick={() => handleSend('add')} disabled={isLoading || !backendOnline}>
              + Add artist
            </button>
            <button className="chat-chip" onClick={() => handleSend('recommend')} disabled={isLoading || !backendOnline}>
              Get recommendations
            </button>
            <button className="chat-chip" onClick={handleReset}>
              Reset chat
            </button>
          </div>
          <Card.Body className="chat-card-body">
            <ListGroup variant="flush" className="message-list">
              {messages.map((msg, index) => (
                <ListGroup.Item
                  key={index}
                  className={`border-0 ${msg.sender === 'user' ? 'text-end' : ''}`}
                >
                  <div className={`chat-message ${msg.sender === 'user' ? 'd-flex flex-column align-items-end' : ''}`}>
                    <div className="bubble-label">{msg.sender === 'user' ? 'You' : 'Assistant'}</div>
                    <div className={`bubble ${msg.sender === 'user' ? 'bubble-user' : 'bubble-bot'}`}>
                      {msg.text}
                    </div>
                  </div>
                </ListGroup.Item>
              ))}
            </ListGroup>
          </Card.Body>
          <Card.Footer className="chat-card-footer">
            <Form.Group className="d-flex gap-2">
              <Form.Control
                className="chat-input"
                type="text"
                placeholder="Describe an artist, genre, or vibe…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading || !backendOnline}
              />
              <Button
                className="chat-send-btn"
                variant="primary"
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim() || !backendOnline}
              >
                {isLoading ? 'Sending…' : 'Send'}
              </Button>
            </Form.Group>
          </Card.Footer>
        </Card>
      </Container>
    </div>
  );
};

export default Chat;
import { useState } from 'react';
import { Container, Card, Form, Button, ListGroup } from 'react-bootstrap';
import './Chat.css';

const Chat = () => {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! I\'m your Memphis Booking Assistant. I can help you:\n\n1. Add a new local artist to the database\n2. Get booking recommendations for a touring artist\n\nWhat would you like to do? (Type "add" or "recommend")' }
  ]);
  const [input, setInput] = useState('');
  const [step, setStep] = useState('choose'); // 'choose', 'name', 'genre', 'confirm', 'done', 'rec-genre', 'rec-done'
  const [artistData, setArtistData] = useState({ name: '', genre: '' });
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);

    const userInput = input;
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
          text: 'Perfect! What genre(s) does the touring artist perform? (e.g., "Indie, Rock, Alternative")' 
        }]);
        setStep('rec-genre');
      } else {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'I didn\'t understand that. Please type "add" to add an artist or "recommend" to get booking recommendations.' 
        }]);
      }
    } else if (step === 'rec-genre') {
      setIsLoading(true);
      try {
        const response = await fetch(`http://127.0.0.1:8000/recommend?touring_genres=${encodeURIComponent(userInput)}`);
        const data = await response.json();

        if (response.ok) {
          let recText = `Here are the top 7 local Memphis artists that match "${userInput}":\n\n`;
          data.recommendations.forEach((rec, idx) => {
            recText += `${idx + 1}. ${rec.artist}\n   Genre: ${rec.genre}\n   Match Score: ${(rec.match_score * 100).toFixed(1)}%\n\n`;
          });
          recText += 'Would you like another recommendation? (yes/no)';
          
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: recText 
          }]);
          setStep('rec-done');
        } else {
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: `Sorry, there was an error: ${data.detail}` 
          }]);
        }
      } catch (error) {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: `Error connecting to the server. Make sure the backend is running on http://127.0.0.1:8000` 
        }]);
      }
      setIsLoading(false);
    } else if (step === 'rec-done') {
      if (userInput.toLowerCase().includes('yes') || userInput.toLowerCase().includes('y')) {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'What genre(s) does the touring artist perform?' 
        }]);
        setStep('rec-genre');
      } else {
        setMessages(prev => [...prev, { 
          sender: 'bot', 
          text: 'Would you like to add an artist or get more recommendations? (Type "add" or "recommend", or "quit" to exit)' 
        }]);
        setStep('choose');
      }
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
          const response = await fetch('http://127.0.0.1:8000/add_artist', {
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
        } catch (error) {
          setMessages(prev => [...prev, { 
            sender: 'bot', 
            text: `Error connecting to the server. Make sure the backend is running on http://127.0.0.1:8000` 
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

  return (
    <Container className="my-4">
      <Card>
        <Card.Header className="bg-primary text-white">
          <h4 className="mb-0">Memphis Booking Assistant</h4>
        </Card.Header>
        <Card.Body style={{ height: '500px', overflowY: 'auto' }}>
          <ListGroup variant="flush">
            {messages.map((msg, index) => (
              <ListGroup.Item 
                key={index} 
                className={`border-0 ${msg.sender === 'user' ? 'text-end' : ''}`}
              >
                <div className={`d-inline-block p-2 rounded ${msg.sender === 'user' ? 'bg-primary text-white' : 'bg-light'}`} style={{ maxWidth: '70%' }}>
                  <small className="fw-bold d-block">{msg.sender === 'user' ? 'You' : 'Bot'}</small>
                  <div style={{ whiteSpace: 'pre-line' }}>{msg.text}</div>
                </div>
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Card.Body>
        <Card.Footer>
          <Form.Group className="d-flex gap-2">
            <Form.Control
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
            <Button 
              variant="primary" 
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </Button>
          </Form.Group>
        </Card.Footer>
      </Card>
    </Container>
  );
};

export default Chat;
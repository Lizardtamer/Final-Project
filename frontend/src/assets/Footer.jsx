import '../../Design/App.css';
import Container from 'react-bootstrap/Container';
import facebookIcon from '../../assets/socialmediaicons/facebook.png';
import instagramIcon from '../../assets/socialmediaicons/instagram.png';
import tiktokIcon from '../../assets/socialmediaicons/tik-tok.png';

export default function Footer(){
    return(
        <>
        <footer className='mfooter'><b>
            <Container className='footText'>
                <div>Havenhaus</div>
                <div>2487 Broad Avenue</div>
                <div>Memphis, TN. 38112</div>
                <div>havenhaus901@gmail.com</div>
            </Container>
            <Container className='socials'>
                <div className='facebook'>
                    <a href="https://www.facebook.com/p/Havenhaus901-61570574391375/"><img src={facebookIcon} alt="havenhaus facebook"></img></a>
                </div>
                <div className='instagram'>
                    <a href="https://www.instagram.com/havenhaus901/"><img src={instagramIcon} alt="havenhaus instagram"></img></a>
                </div>
                <div className='tiktok'>
                    <a href="https://www.tiktok.com/@havenhaus901"><img src={tiktokIcon} alt="havenhaus tiktok"></img></a>
                </div>
            </Container>
        </b></footer>
        </>
    )
}
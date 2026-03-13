import Container from 'react-bootstrap/Container';

export default function myFooter {
  return(
        <>
        <footer className='mfooter'><b>
            <Container className='footText'>
                <div>Benjamin Reese</div>
                <div>Developer, Musician, Veteran</div>
                <div>Memphis, Tennessee</div>
                <div>havenhaus901@gmail.com</div>
            </Container>
            <Container className='socials'>
                <div className='linkedin'>
                    <a href=""><img src={linkedinIcon} alt="Ben's linkedin"></img></a>
                </div>
                <div className='github'>
                    <a href=""><img src={githubIcon} alt="Ben's github"></img></a>
                </div>
                <div className='facebook'>
                    <a href=""><img src={facebookIcon} alt="Ben's facebook"></img></a>
                </div>
                <div className='instagram'>
                    <a href=""><img src={instagramIcon} alt="Ben's instagram"></img></a>
                </div>
            </Container>
        </b></footer>
        </>
    )
}
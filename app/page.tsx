import Nav from '@/components/Nav'
import Hero from '@/components/Hero'
import ChatDemo from '@/components/ChatDemo'
import HowItWorks from '@/components/HowItWorks'
import Argument from '@/components/Argument'
import PriceProof from '@/components/PriceProof'
import CTASection from '@/components/CTASection'
import WaitlistForm from '@/components/WaitlistForm'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <div className="container"><hr className="divider" /></div>
        <ChatDemo />
        <div className="container"><hr className="divider" /></div>
        <HowItWorks />
        <div className="container"><hr className="divider" /></div>
        <Argument />
        <div className="container"><hr className="divider" /></div>
        <PriceProof />
        <div className="container"><hr className="divider" /></div>
        <CTASection />
        <div className="container"><hr className="divider" /></div>
        <WaitlistForm />
      </main>
      <Footer />
    </>
  )
}

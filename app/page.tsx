import Nav from '@/components/Nav'
import Hero from '@/components/Hero'
import ChatDemo from '@/components/ChatDemo'
import HowItWorks from '@/components/HowItWorks'
import Argument from '@/components/Argument'
import PriceProof from '@/components/PriceProof'
import WaitlistForm from '@/components/WaitlistForm'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <ChatDemo />
        <HowItWorks />
        <Argument />
        <PriceProof />
        <WaitlistForm />
      </main>
      <Footer />
    </>
  )
}

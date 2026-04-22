/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // In development, proxy /_/backend/* to the local FastAPI server.
    // On Vercel, experimentalServices handles this routing natively.
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/_/backend/:path*',
          destination: 'http://localhost:8000/:path*',
        },
      ]
    }
    return []
  },
}

module.exports = nextConfig

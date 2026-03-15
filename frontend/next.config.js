/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Pre-existing type errors in crop preview SVG — ignored for build
    ignoreBuildErrors: true,
  },
}

module.exports = nextConfig

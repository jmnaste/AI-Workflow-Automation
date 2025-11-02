import { useEffect, useState } from 'react'

type Health = { status: string }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: Health) => setHealth(data))
      .catch((e: any) => setError(String(e)))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif', padding: 24 }}>
      <h1>AI Workflow UI</h1>
      <p>Same-origin API under <code>/api</code>.</p>
      <h3>API health</h3>
      {health && <pre>{JSON.stringify(health, null, 2)}</pre>}
      {error && <pre style={{ color: 'crimson' }}>{error}</pre>}
    </div>
  )
}

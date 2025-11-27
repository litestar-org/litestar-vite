import { useState } from "react"

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <h1>spa-react</h1>
      <p>React + Litestar + Vite</p>
      <div className="card">
        <button type="button" onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
      </div>
    </div>
  )
}

export default App

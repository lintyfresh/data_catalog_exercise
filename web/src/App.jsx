import { useEffect, useState } from 'react'

export default function App() {
  const [assets, setAssets] = useState(null)
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    fetch('/catalog.json')
      .then(r => r.json())
      .then(data => {
        setAssets(data)
        setSelected(data[0]?.path)
      })
  }, [])

  if (!assets) return <p className="loading">Loading catalog…</p>

  const shown = assets.filter(a => a.path.toLowerCase().includes(filter.toLowerCase()))
  const asset = assets.find(a => a.path === selected)
  const nDelta = assets.filter(a => a.kind === 'delta').length

  return (
    <div className="layout">
      <aside>
        <h1>Lakehouse Catalog</h1>
        <input
          placeholder="Filter assets…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
        <ul>
          {shown.map(a => (
            <li
              key={a.path}
              className={a.path === selected ? 'active' : ''}
              onClick={() => setSelected(a.path)}
            >
              <span className={`badge ${a.kind}`}>{a.kind === 'delta' ? 'delta' : a.format}</span>
              <span className="path">{a.path}</span>
            </li>
          ))}
        </ul>
        <p className="count">
          {assets.length} assets · {nDelta} delta tables · {assets.length - nDelta} plain files
        </p>
      </aside>
      <main>{asset ? <Asset a={asset} /> : <p>Select an asset</p>}</main>
    </div>
  )
}

function Asset({ a }) {
  return (
    <>
      <div className="asset-head">
        <h2>{a.path}</h2>
        <span className={`badge ${a.kind}`}>{a.kind === 'delta' ? 'Delta table' : `${a.format} file`}</span>
      </div>
      {a.error ? (
        <p className="error">Could not read: {a.error}</p>
      ) : (
        <>
          <h3>Schema · {Object.keys(a.schema).length} columns</h3>
          <table>
            <thead>
              <tr><th>column</th><th>type</th></tr>
            </thead>
            <tbody>
              {Object.entries(a.schema).map(([col, typ]) => (
                <tr key={col}><td>{col}</td><td className="type">{typ}</td></tr>
              ))}
            </tbody>
          </table>
          {a.history ? (
            <>
              <h3>History · {a.history.length} commits</h3>
              <table>
                <thead>
                  <tr><th>version</th><th>timestamp (UTC)</th><th>operation</th></tr>
                </thead>
                <tbody>
                  {a.history.map(h => (
                    <tr key={h.version}>
                      <td>v{h.version}</td>
                      <td>{h.timestamp}</td>
                      <td><span className={`op op-${h.operation}`}>{h.operation}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="note">Plain file — no version history.</p>
          )}
        </>
      )}
    </>
  )
}

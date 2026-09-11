import { Link, useNavigate, useLocation } from 'react-router-dom'

export default function Navbar() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const role      = localStorage.getItem('role')
  const name      = localStorage.getItem('name')

  const logout = () => {
    localStorage.clear()
    navigate('/login')
  }

  const links = [
    { to: '/scan',      label: '🔍 New Scan' },
    { to: '/history',   label: '📋 History' },
    ...(role === 'ADMIN' ? [{ to: '/dashboard', label: '📊 Dashboard' }] : []),
  ]

  return (
    <nav style={{
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div className="navbar-inner">
        {/* Logo */}
        <Link to="/scan" style={{ display:'flex', alignItems:'center', gap:10, textDecoration:'none', flexShrink: 0 }}>
          <div style={{ width:32, height:32, background:'var(--accent)', borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center', fontSize:16 }}>⚖️</div>
          <div>
            <div style={{ fontWeight:800, fontSize:14, color:'var(--text-primary)', lineHeight:1.2 }}>Legal Metrology</div>
            <div className="nav-subtitle" style={{ fontSize:10, color:'var(--text-muted)', fontWeight:600, letterSpacing:'0.05em', textTransform:'uppercase' }}>Compliance Scanner</div>
          </div>
        </Link>

        {/* Nav links */}
        <div className="nav-links-wrap">
          {links.map(l => (
            <Link key={l.to} to={l.to} style={{
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              textDecoration: 'none',
              color: location.pathname === l.to ? 'var(--accent)' : 'var(--text-secondary)',
              background: location.pathname === l.to ? 'var(--accent-dim)' : 'transparent',
              transition: 'all 0.15s',
            }}>
              {l.label}
            </Link>
          ))}
        </div>

        {/* User info + logout */}
        <div style={{ display:'flex', alignItems:'center', gap:10, flexShrink: 0 }}>
          <div className="nav-user-name" style={{ textAlign:'right' }}>
            <div style={{ fontSize:13, fontWeight:600, color:'var(--text-primary)' }}>{name}</div>
            <div style={{ fontSize:11, color: role==='ADMIN' ? 'var(--review)' : 'var(--accent)', fontWeight:700, textTransform:'uppercase' }}>{role}</div>
          </div>
          <button onClick={logout} className="btn btn-ghost" style={{ padding:'6px 10px', fontSize:12, whiteSpace: 'nowrap' }}>Sign Out</button>
        </div>
      </div>
    </nav>
  )
}

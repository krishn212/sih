import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export default function LoginPage() {
  const navigate = useNavigate()
  const [mode, setMode]   = useState('login') // 'login' | 'register'
  const [form, setForm]   = useState({ name:'', email:'', password:'', role:'INSPECTOR' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handle = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const url = mode === 'login' ? '/auth/login' : '/auth/register'
      const { data } = await client.post(url, form)
      localStorage.setItem('token',   data.access_token)
      localStorage.setItem('role',    data.role)
      localStorage.setItem('name',    data.name)
      localStorage.setItem('user_id', data.user_id)
      navigate('/scan')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--bg-base)', padding:24 }}>
      <div style={{ width:'100%', maxWidth:420 }}>
        {/* Header */}
        <div style={{ textAlign:'center', marginBottom:32 }}>
          <div style={{ width:56, height:56, background:'var(--accent)', borderRadius:16, display:'flex', alignItems:'center', justifyContent:'center', fontSize:28, margin:'0 auto 16px' }}>⚖️</div>
          <h1 style={{ fontSize:22, fontWeight:800 }}>Legal Metrology Scanner</h1>
          <p style={{ color:'var(--text-muted)', fontSize:13, marginTop:6 }}>Department of Consumer Affairs · Government of India</p>
        </div>

        <div className="card">
          {/* Tab toggle */}
          <div style={{ display:'flex', background:'var(--bg-elevated)', borderRadius:8, padding:4, marginBottom:24 }}>
            {['login','register'].map(m => (
              <button key={m} onClick={() => setMode(m)} style={{
                flex:1, padding:'8px', borderRadius:6, border:'none', fontSize:13, fontWeight:600,
                background: mode===m ? 'var(--accent)' : 'transparent',
                color: mode===m ? '#fff' : 'var(--text-muted)',
                transition: 'all 0.15s',
              }}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:16 }}>
            {mode === 'register' && (
              <div className="form-group">
                <label htmlFor="name">Full Name</label>
                <input id="name" name="name" type="text" value={form.name} onChange={handle} placeholder="Officer name" required />
              </div>
            )}
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input id="email" name="email" type="email" value={form.email} onChange={handle} placeholder="officer@doca.gov.in" required />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" value={form.password} onChange={handle} placeholder="••••••••" required />
            </div>
            {mode === 'register' && (
              <div className="form-group">
                <label htmlFor="role">Role</label>
                <select id="role" name="role" value={form.role} onChange={handle}>
                  <option value="INSPECTOR">Inspector</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
            )}

            {error && <div className="alert alert-error">{error}</div>}

            <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
              {loading ? <><span className="spinner" style={{width:16,height:16}} /> Processing…</> : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>

        <p style={{ textAlign:'center', fontSize:12, color:'var(--text-muted)', marginTop:20 }}>
          Legal Metrology Compliance Scanner v1.0 · SIH 2026 #26034
        </p>
      </div>
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import client, { API_BASE } from '../api/client'

const CALIBRATION_OPTIONS = [
  { value:'ARUCO',    label:'ArUco Marker',  desc:'10cm×10cm printed marker — highest accuracy, full tilt correction', icon:'🎯' },
  { value:'ID_CARD',  label:'ID Card',        desc:'Aadhaar/PAN/DL (85.6mm×53.98mm) — geometry only, nothing stored', icon:'🪪' },
  { value:'COIN',     label:'Coin (₹5/₹1)',   desc:'Indian coin — scale only, no tilt correction', icon:'🪙' },
  { value:'NONE',     label:'No Reference',   desc:'Distance estimate — lowest confidence, MANUAL REVIEW likely', icon:'📏' },
]

const DEMO_PRESETS = [
  {
    file: 'compliant_sample.jpg',
    label: '🟢 Compliant Sample',
    badge: 'PASS',
    desc: 'NutriGold Almonds · All 10 Rules Pass',
    brand: 'NutriGold Almonds',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--pass)',
  },
  {
    file: 'violation_sample.jpg',
    label: '🔴 Violation Sample',
    badge: 'FAIL',
    desc: 'Spicy Nuts · MRP, gm & Math Violations',
    brand: 'Crunchy Bites Spicy Nuts',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--fail)',
  },
  {
    file: 'manual_review_sample.jpg',
    label: '🟡 Manual Review Sample',
    badge: 'MANUAL REVIEW',
    desc: 'Himalayan Tea · Uncalibrated Packaging',
    brand: 'Himalayan Organic Green Tea',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--review)',
  },
]

const STEPS = ['Blur Check', 'Calibration', 'OCR', 'Field Detection', 'Rules', 'Done']

export default function ScanPage() {
  const navigate  = useNavigate()
  const fileRef   = useRef(null)
  const nativeCameraRef = useRef(null)
  const videoRef  = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const [file, setFile]         = useState(null)
  const [preview, setPreview]   = useState(null)
  const [dragging, setDragging] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraFacing, setCameraFacing] = useState('environment') // 'environment' | 'user'
  const [cameraLoading, setCameraLoading] = useState(false)
  const [cameraError, setCameraError] = useState('')

  const [form, setForm]         = useState({
    calibration_type: 'ARUCO',
    surface_type: 'FLAT',
    brand_name: '',
    category: 'General',
    is_imported: false,
  })
  const [scanning, setScanning]     = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError]           = useState('')

  const compressImage = async (originalFile) => {
    return new Promise((resolve) => {
      if (!originalFile || originalFile.size < 500 * 1024) return resolve(originalFile)
      const img = new Image()
      const reader = new FileReader()
      reader.onload = (e) => {
        img.src = e.target.result
        img.onload = () => {
          const maxDim = 1600
          let w = img.width
          let h = img.height
          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w)
              w = maxDim
            } else {
              w = Math.round((w * maxDim) / h)
              h = maxDim
            }
          }
          const canvas = document.createElement('canvas')
          canvas.width = w
          canvas.height = h
          const ctx = canvas.getContext('2d')
          ctx.drawImage(img, 0, 0, w, h)
          canvas.toBlob((blob) => {
            if (blob) {
              resolve(new File([blob], originalFile.name.replace(/\.[^/.]+$/, ".jpg"), { type: 'image/jpeg' }))
            } else {
              resolve(originalFile)
            }
          }, 'image/jpeg', 0.88)
        }
        img.onerror = () => resolve(originalFile)
      }
      reader.onerror = () => resolve(originalFile)
      reader.readAsDataURL(originalFile)
    })
  }

  const pickFile = async f => {
    if (!f) return
    const optimized = await compressImage(f)
    setFile(optimized)
    setPreview(URL.createObjectURL(optimized))
    setError('')
    setCameraError('')
  }

  const startCamera = async (facing = cameraFacing) => {
    try {
      setCameraLoading(true)
      setCameraError('')
      stopCamera()

      const constraints = {
        video: {
          facingMode: facing,
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      setCameraOpen(true)
      setCameraFacing(facing)

      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play().catch(e => console.warn('Video play error:', e))
        }
      }, 100)
    } catch (err) {
      console.error('Camera error:', err)
      setCameraError(err.name === 'NotAllowedError' ? 'Camera permission was denied. Please allow camera access in your browser settings.' : (err.message || 'Unable to access camera.'))
      setCameraOpen(false)
    } finally {
      setCameraLoading(false)
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraOpen(false)
  }

  const toggleFacing = () => {
    const next = cameraFacing === 'environment' ? 'user' : 'environment'
    startCamera(next)
  }

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    const w = video.videoWidth || 1280
    const h = video.videoHeight || 720
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, w, h)
    canvas.toBlob((blob) => {
      if (blob) {
        const snapFile = new File([blob], `camera_snap_${Date.now()}.jpg`, { type: 'image/jpeg' })
        pickFile(snapFile)
        stopCamera()
      }
    }, 'image/jpeg', 0.95)
  }

  useEffect(() => {
    return () => stopCamera()
  }, [])

  const loadDemoSample = async (preset) => {
    try {
      const resp = await fetch(`${API_BASE}/demo_samples/${preset.file}`)
      if (!resp.ok) throw new Error('Failed to fetch sample')
      const blob = await resp.blob()
      const f = new File([blob], preset.file, { type: 'image/jpeg' })
      pickFile(f)
      setForm(prev => ({
        ...prev,
        brand_name: preset.brand,
        category: preset.category,
        calibration_type: preset.cal,
      }))
    } catch (e) {
      setError(`Could not load preset "${preset.file}": Ensure backend is running.`)
    }
  }

  const onDrop = e => {
    e.preventDefault(); setDragging(false)
    pickFile(e.dataTransfer.files[0])
  }

  const handle = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const submit = async e => {
    e.preventDefault()
    if (!file) return setError('Please select a product label image.')
    setScanning(true); setCurrentStep(0); setError('')

    // Simulate step progression for UX
    const stepTimer = setInterval(() => setCurrentStep(s => Math.min(s + 1, STEPS.length - 2)), 1200)

    try {
      const fd = new FormData()
      fd.append('file', file)
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))

      const { data } = await client.post('/scan/upload', fd)
      clearInterval(stepTimer)
      setCurrentStep(STEPS.length - 1)
      setTimeout(() => navigate(`/evidence/${data.scan_id}`, { state: { scanData: data } }), 600)
    } catch (err) {
      clearInterval(stepTimer)
      setScanning(false); setCurrentStep(0)
      setError(err.response?.data?.detail || 'Scan failed. Check your image and try again.')
    }
  }

  return (
    <div className="page">
      <div style={{ marginBottom:28 }}>
        <h1>New Inspection Scan</h1>
        <p style={{ color:'var(--text-secondary)', marginTop:4 }}>Photograph a product label to check compliance against Legal Metrology Rules 2011</p>
      </div>

      <form onSubmit={submit} className="scan-layout">
        {/* Left: upload + options */}
        <div style={{ display:'flex', flexDirection:'column', gap:20 }}>

          {/* Quick Demo Test Presets */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
                ⚡ Quick Load Test Packaging Samples:
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                One-click test suite for live inspection demo
              </span>
            </div>
            <div className="demo-presets-grid">
              {DEMO_PRESETS.map((p) => (
                <button
                  key={p.file}
                  type="button"
                  onClick={() => loadDemoSample(p)}
                  className="btn btn-ghost"
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
                    padding: '10px 12px', borderRadius: 8,
                    border: `1px solid ${file?.name === p.file ? p.color : 'var(--border)'}`,
                    background: file?.name === p.file ? 'var(--bg-elevated)' : 'transparent',
                    cursor: 'pointer', textAlign: 'left', gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <strong style={{ fontSize: 12, color: 'var(--text-primary)' }}>{p.label}</strong>
                    <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: `${p.color}22`, color: p.color, fontWeight: 700 }}>
                      {p.badge}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{p.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Hidden inputs for camera capture & file picking */}
          <input ref={fileRef} type="file" accept="image/*" style={{ display:'none' }} onChange={e => pickFile(e.target.files[0])} />
          <input ref={nativeCameraRef} type="file" accept="image/*" capture="environment" style={{ display:'none' }} onChange={e => pickFile(e.target.files[0])} />
          <canvas ref={canvasRef} style={{ display:'none' }} />

          {/* Capture Method Controls */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => {
                if (cameraOpen) stopCamera()
                else startCamera()
              }}
              className="btn btn-primary"
              style={{
                flex: 1, minWidth: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                background: cameraOpen ? '#dc2626' : 'var(--accent)',
              }}
            >
              {cameraLoading ? '⏳ Starting Camera...' : cameraOpen ? '✖ Close Viewfinder' : '📸 Open In-App Camera'}
            </button>

            <button
              type="button"
              onClick={() => nativeCameraRef.current?.click()}
              className="btn btn-ghost"
              style={{
                flex: 1, minWidth: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                border: '1px solid var(--border)', background: 'var(--bg-surface)'
              }}
            >
              📱 Mobile Camera Shutter
            </button>

            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="btn btn-ghost"
              style={{
                flex: 1, minWidth: 130, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                border: '1px solid var(--border)', background: 'var(--bg-surface)'
              }}
            >
              📁 Browse Files
            </button>
          </div>

          {/* Camera Error Message */}
          {cameraError && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--fail)', borderRadius: 8,
              padding: '12px 14px', fontSize: 13, color: 'var(--fail)', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
            }}>
              <span>⚠️ {cameraError}</span>
              <button type="button" onClick={() => nativeCameraRef.current?.click()} style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontWeight: 600, textDecoration: 'underline' }}>
                Use phone camera instead
              </button>
            </div>
          )}

          {/* Live In-App Viewfinder */}
          {cameraOpen ? (
            <div style={{
              position: 'relative', borderRadius: 'var(--radius-lg)', overflow: 'hidden',
              border: '2px solid var(--accent)', background: '#000', display: 'flex', flexDirection: 'column'
            }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{ width: '100%', minHeight: 320, maxHeight: 420, objectFit: 'contain', background: '#0a0a0a', display: 'block' }}
              />

              {/* Viewfinder Target Framing Overlay */}
              <div style={{
                position: 'absolute', top: '10%', left: '8%', right: '8%', bottom: '26%',
                border: '2px dashed rgba(59, 130, 246, 0.8)', borderRadius: 12,
                pointerEvents: 'none', display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
                padding: 8, background: 'rgba(59, 130, 246, 0.04)',
                boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.35)'
              }}>
                <span style={{
                  fontSize: 11, background: 'rgba(15, 23, 42, 0.85)', color: '#38bdf8', padding: '3px 10px',
                  borderRadius: 99, fontWeight: 700, letterSpacing: '0.04em', border: '1px solid rgba(56, 189, 248, 0.3)'
                }}>
                  🎯 ALIGN PACKAGING & ARUCO MARKER INSIDE
                </span>
              </div>

              {/* Bottom In-App Camera Controls */}
              <div style={{
                padding: '12px 16px', background: 'rgba(15, 23, 42, 0.95)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderTop: '1px solid var(--border)'
              }}>
                <button
                  type="button"
                  onClick={toggleFacing}
                  className="btn btn-ghost"
                  style={{ fontSize: 13, border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}
                  title="Switch between front and back cameras"
                >
                  🔄 Flip Camera
                </button>

                <button
                  type="button"
                  onClick={capturePhoto}
                  className="btn btn-primary"
                  style={{
                    padding: '10px 28px', fontSize: 14, fontWeight: 700,
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: 'linear-gradient(135deg, #10b981, #059669)', border: 'none',
                    boxShadow: '0 0 16px rgba(16, 185, 129, 0.4)'
                  }}
                >
                  📸 SNAP PHOTO
                </button>

                <button
                  type="button"
                  onClick={stopCamera}
                  className="btn btn-ghost"
                  style={{ fontSize: 13, color: 'var(--text-muted)' }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            /* Drop zone or Captured Photo Preview */
            <div
              className={`drop-zone ${dragging ? 'dragging' : ''}`}
              onClick={() => !preview && fileRef.current.click()}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              {preview ? (
                <div>
                  <img src={preview} alt="Captured Preview" style={{ maxHeight: 280, margin: '0 auto', borderRadius: 8, border: '1px solid var(--border)' }} />
                  <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 14 }}>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); startCamera(); }}
                      className="btn btn-ghost"
                      style={{ fontSize: 12, border: '1px solid var(--border)' }}
                    >
                      📸 Retake with Camera
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); fileRef.current.click(); }}
                      className="btn btn-ghost"
                      style={{ fontSize: 12, border: '1px solid var(--border)' }}
                    >
                      📁 Choose Different Image
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="drop-zone-icon">📷</div>
                  <h3 style={{ marginBottom: 8 }}>Snap photo with camera or drop image here</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    Live webcam viewfinder, phone camera, or JPG, PNG, WEBP files supported
                  </p>
                </>
              )}
            </div>
          )}

          {/* Product info */}
          <div className="card">
            <h4 style={{ marginBottom:16 }}>Product Information</h4>
            <div className="grid-2">
              <div className="form-group">
                <label htmlFor="brand_name">Brand / Product Name</label>
                <input id="brand_name" name="brand_name" value={form.brand_name} onChange={handle} placeholder="e.g. Maggi, Haldirams" />
              </div>
              <div className="form-group">
                <label htmlFor="category">Category</label>
                <select id="category" name="category" value={form.category} onChange={handle}>
                  <option>General</option>
                  <option>Food</option>
                  <option>Beverages</option>
                  <option>Personal Care</option>
                  <option>Household</option>
                  <option>Pharmaceuticals</option>
                </select>
              </div>
            </div>
            <div style={{ marginTop:12, display:'flex', alignItems:'center', gap:8 }}>
              <input id="is_imported" name="is_imported" type="checkbox" checked={form.is_imported} onChange={handle} style={{ width:'auto' }} />
              <label htmlFor="is_imported" style={{ textTransform:'none', letterSpacing:'normal', fontSize:14, fontWeight:500 }}>
                This is an imported product (country of origin check applies)
              </label>
            </div>
          </div>
        </div>

        {/* Right: calibration + surface + submit */}
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <h4 style={{ marginBottom:4 }}>Calibration Reference</h4>
            <p style={{ fontSize:12, color:'var(--text-muted)', marginBottom:16 }}>Place your reference object beside the product label</p>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {CALIBRATION_OPTIONS.map(opt => (
                <label key={opt.value} style={{
                  display:'flex', alignItems:'flex-start', gap:12, padding:12, borderRadius:8, cursor:'pointer',
                  border: `1px solid ${form.calibration_type === opt.value ? 'var(--accent)' : 'var(--border)'}`,
                  background: form.calibration_type === opt.value ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  transition: 'all 0.15s',
                }}>
                  <input type="radio" name="calibration_type" value={opt.value} checked={form.calibration_type === opt.value} onChange={handle} style={{ marginTop:2, width:'auto', accentColor:'var(--accent)' }} />
                  <div>
                    <div style={{ fontWeight:600, fontSize:13 }}>{opt.icon} {opt.label}</div>
                    <div style={{ fontSize:11, color:'var(--text-muted)', marginTop:2 }}>{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="card">
            <h4 style={{ marginBottom:12 }}>Surface Type</h4>
            <div style={{ display:'flex', gap:8 }}>
              {[{v:'FLAT', l:'📦 Flat', d:'Boxes, cartons, pouches'}, {v:'CURVED', l:'🥫 Curved', d:'Bottles, cans'}].map(o => (
                <label key={o.v} style={{
                  flex:1, padding:12, borderRadius:8, cursor:'pointer', textAlign:'center',
                  border: `1px solid ${form.surface_type === o.v ? 'var(--accent)' : 'var(--border)'}`,
                  background: form.surface_type === o.v ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  transition: 'all 0.15s',
                }}>
                  <input type="radio" name="surface_type" value={o.v} checked={form.surface_type === o.v} onChange={handle} style={{ display:'none' }} />
                  <div style={{ fontWeight:600, fontSize:13 }}>{o.l}</div>
                  <div style={{ fontSize:11, color:'var(--text-muted)' }}>{o.d}</div>
                </label>
              ))}
            </div>
          </div>

          {/* Processing steps indicator */}
          {scanning && (
            <div className="card">
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
                <span className="spinner" />
                <span style={{ fontWeight:600, fontSize:14 }}>Processing…</span>
              </div>
              {STEPS.map((step, i) => (
                <div key={step} style={{ display:'flex', alignItems:'center', gap:10, padding:'6px 0' }}>
                  <div style={{
                    width:20, height:20, borderRadius:'50%', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:11,
                    background: i < currentStep ? 'var(--pass)' : i === currentStep ? 'var(--accent)' : 'var(--border)',
                    color: i <= currentStep ? '#fff' : 'var(--text-muted)',
                  }}>
                    {i < currentStep ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize:13, color: i <= currentStep ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: i === currentStep ? 600 : 400 }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-lg" disabled={scanning || !file}>
            {scanning ? <><span className="spinner" style={{width:18,height:18}} /> Scanning…</> : '🔍 Run Compliance Scan'}
          </button>

          <p style={{ fontSize:11, color:'var(--text-muted)', textAlign:'center' }}>
            Results are AI-assisted. All verdicts reference exact Legal Metrology Rules 2011 clauses.
          </p>
        </div>
      </form>
    </div>
  )
}

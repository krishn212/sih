import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import ScanPage from './pages/ScanPage'
import EvidencePage from './pages/EvidencePage'
import HistoryPage from './pages/HistoryPage'
import DashboardPage from './pages/DashboardPage'
import Navbar from './components/Navbar'

function ProtectedRoute({ children, adminOnly = false }) {
  const token = localStorage.getItem('token')
  const role  = localStorage.getItem('role')
  if (!token) return <Navigate to="/login" replace />
  if (adminOnly && role !== 'ADMIN') return <Navigate to="/scan" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={
          <ProtectedRoute>
            <Navbar />
            <Routes>
              <Route path="/scan"      element={<ScanPage />} />
              <Route path="/evidence/:scanId" element={<EvidencePage />} />
              <Route path="/history"  element={<HistoryPage />} />
              <Route path="/dashboard" element={
                <ProtectedRoute adminOnly>
                  <DashboardPage />
                </ProtectedRoute>
              } />
              <Route path="*" element={<Navigate to="/scan" replace />} />
            </Routes>
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}

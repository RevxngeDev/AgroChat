import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { isAuthenticated } from "./api";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import QueryLogs from "./pages/QueryLogs";
import Feedback from "./pages/Feedback";
import Analytics from "./pages/Analytics";

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/query-logs" element={<QueryLogs />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/analytics" element={<Analytics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
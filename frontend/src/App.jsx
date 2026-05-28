import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Review from "./pages/Review";
import Upload from "./pages/Upload";

function PrivateRoute({ children }) {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="review" element={<Review />} />
        <Route path="upload" element={<Upload />} />
      </Route>
    </Routes>
  );
}

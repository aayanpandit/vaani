import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import AdminLayout from "./components/AdminLayout";
import AdminProtectedRoute from "./components/AdminProtectedRoute";
import AdminAppointments from "./pages/AdminAppointments";
import AdminAudit from "./pages/AdminAudit";
import AdminCustomers from "./pages/AdminCustomers";
import AdminDashboard from "./pages/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";
import AdminProfile from "./pages/AdminProfile";
import CustomerDetails from "./pages/CustomerDetails";
import UserDashboard from "./pages/UserDashboard";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public smartphone calling interface */}
        <Route
          path="/"
          element={<Navigate to="/user" replace />}
        />

        <Route
          path="/user"
          element={<UserDashboard />}
        />

        <Route
          path="/user/dashboard"
          element={<Navigate to="/user" replace />}
        />

        {/* Admin login */}
        <Route
          path="/admin/login"
          element={<AdminLogin />}
        />

        {/* Protected admin console */}
        <Route element={<AdminProtectedRoute />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />

            <Route
              path="appointments"
              element={<AdminAppointments />}
            />

            <Route
              path="customers"
              element={<AdminCustomers />}
            />

            <Route
              path="customers/:phoneNumber"
              element={<CustomerDetails />}
            />

            <Route
              path="audit"
              element={<AdminAudit />}
            />

            <Route
              path="profile"
              element={<AdminProfile />}
            />
          </Route>
        </Route>

        <Route
          path="*"
          element={<Navigate to="/user" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAdminToken } from "../utils/adminAuth";

function AdminProtectedRoute() {
  const location = useLocation();
  if (!getAdminToken()) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export default AdminProtectedRoute;

import {
  Clock3,
  KeyRound,
  LogOut,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import {
  clearAdminSession,
  getStoredAdmin,
} from "../utils/adminAuth";

function AdminProfile() {
  const navigate = useNavigate();
  const admin = getStoredAdmin();

  const logout = () => {
    clearAdminSession();
    navigate("/admin/login", { replace: true });
  };

  const initials = (admin?.full_name || "Admin")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="bank-content bank-profile-page">
      <section className="bank-page-heading bank-profile-heading">
        <div>
          <p className="bank-section-label">
            ACCOUNT MANAGEMENT
          </p>
          <h1>Admin profile</h1>
          <p>
            Review your administrator identity, access role,
            and active secure session.
          </p>
        </div>

        <div className="bank-profile-session-pill">
          <ShieldCheck size={17} />
          Secure session active
        </div>
      </section>

      <section className="bank-profile-overview-card">
        <div className="bank-profile-overview-left">
          <div className="bank-profile-hero-avatar">
            {initials}
          </div>

          <div>
            <span>AUTHENTICATED ADMINISTRATOR</span>
            <h2>{admin?.full_name || "Administrator"}</h2>
            <p>{admin?.email || "No email available"}</p>
          </div>
        </div>

        <div className="bank-profile-overview-right">
          <div>
            <span>Access role</span>
            <strong>{admin?.role || "admin"}</strong>
          </div>

          <div>
            <span>Account status</span>
            <strong className="bank-profile-active-status">
              <i />
              Active
            </strong>
          </div>

          <div>
            <span>Last login</span>
            <strong>
              {admin?.last_login_at
                ? new Date(
                    admin.last_login_at
                  ).toLocaleString("en-IN")
                : "Current session"}
            </strong>
          </div>
        </div>
      </section>

      <section className="bank-profile-grid">
        <article className="bank-profile-details-card">
          <div className="bank-profile-card-heading">
            <div className="bank-profile-card-icon">
              <UserRound size={20} />
            </div>

            <div>
              <h2>Account details</h2>
              <p>Administrator identity information</p>
            </div>
          </div>

          <div className="bank-profile-detail-list">
            <div>
              <span className="bank-profile-detail-icon">
                <UserRound size={18} />
              </span>

              <div>
                <small>Full name</small>
                <strong>{admin?.full_name || "—"}</strong>
              </div>
            </div>

            <div>
              <span className="bank-profile-detail-icon">
                <Mail size={18} />
              </span>

              <div>
                <small>Email address</small>
                <strong>{admin?.email || "—"}</strong>
              </div>
            </div>

            <div>
              <span className="bank-profile-detail-icon">
                <ShieldCheck size={18} />
              </span>

              <div>
                <small>Access role</small>
                <strong>{admin?.role || "admin"}</strong>
              </div>
            </div>

            <div>
              <span className="bank-profile-detail-icon">
                <Clock3 size={18} />
              </span>

              <div>
                <small>Last successful login</small>
                <strong>
                  {admin?.last_login_at
                    ? new Date(
                        admin.last_login_at
                      ).toLocaleString("en-IN")
                    : "Current session"}
                </strong>
              </div>
            </div>
          </div>
        </article>

        <aside className="bank-profile-security-card">
          <div className="bank-profile-card-heading">
            <div className="bank-profile-card-icon security">
              <KeyRound size={20} />
            </div>

            <div>
              <h2>Security</h2>
              <p>Current access and session controls</p>
            </div>
          </div>

          <div className="bank-profile-security-status">
            <ShieldCheck size={22} />

            <div>
              <strong>Protected administrator session</strong>
              <span>
                Your current session is authenticated and
                access-controlled.
              </span>
            </div>
          </div>

          <div className="bank-profile-security-row">
            <span>Authentication</span>
            <strong>JWT access token</strong>
          </div>

          <div className="bank-profile-security-row">
            <span>Session status</span>
            <strong className="bank-profile-active-status">
              <i />
              Active
            </strong>
          </div>

          <button
            type="button"
            className="bank-profile-logout-button"
            onClick={logout}
          >
            <LogOut size={18} />
            Secure logout
          </button>
        </aside>
      </section>
    </div>
  );
}

export default AdminProfile;
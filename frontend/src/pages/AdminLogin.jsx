import { useState } from "react";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { saveAdminSession } from "../utils/adminAuth";

const API_BASE_URL = "http://127.0.0.1:8000";

function AdminLogin() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to sign in."
        );
      }

      saveAdminSession(data.access_token, data.admin);

      navigate(
        location.state?.from || "/admin",
        { replace: true }
      );
    } catch (requestError) {
      setError(
        requestError.message ||
          "Unable to reach the secure admin service."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="secure-login-page">
      <section className="secure-login-visual">
        <div className="secure-login-brand">
          <div className="secure-login-brand-mark">
            <ShieldCheck size={28} />
          </div>

          <div>
            <strong>VAANI</strong>
            <span>Administrative Operations Console</span>
          </div>
        </div>

        <div className="secure-login-copy">
          <p>SECURE ADMINISTRATIVE ACCESS</p>

          <h1>
            Control appointment operations with confidence.
          </h1>

          <span>
            Manage customers, appointments, profile access, and
            protected activity records from one secure workspace.
          </span>

          <div className="secure-login-features">
            <div>
              <ShieldCheck size={18} />
              <span>Protected administrator session</span>
            </div>

            <div>
              <LockKeyhole size={18} />
              <span>Restricted appointment modifications</span>
            </div>

            <div>
              <Mail size={18} />
              <span>Account-based access and audit visibility</span>
            </div>
          </div>
        </div>

        <div className="secure-login-authorised">
          <i />
          Authorised personnel only
        </div>
      </section>

      <section className="secure-login-panel">
        <form
          className="secure-login-card"
          onSubmit={handleSubmit}
        >
          <div className="secure-login-mobile-logo">
            <ShieldCheck size={25} />
          </div>

          <div className="secure-login-heading">
            <p>VAANI ADMIN</p>
            <h2>Secure sign in</h2>
            <span>
              Enter your administrator credentials to continue.
            </span>
          </div>

          <label className="secure-login-field">
            <span>Email address</span>

            <div>
              <Mail size={18} />

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="admin@company.com"
                autoComplete="email"
                required
              />
            </div>
          </label>

          <label className="secure-login-field">
            <span>Password</span>

            <div>
              <LockKeyhole size={18} />

              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />

              <button
                type="button"
                onClick={() =>
                  setShowPassword((current) => !current)
                }
                aria-label={
                  showPassword
                    ? "Hide password"
                    : "Show password"
                }
              >
                {showPassword ? (
                  <EyeOff size={18} />
                ) : (
                  <Eye size={18} />
                )}
              </button>
            </div>
          </label>

          {error && (
            <div className="secure-login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="secure-login-submit"
            disabled={loading}
          >
            <span>
              {loading
                ? "Authenticating..."
                : "Sign in securely"}
            </span>

            <ArrowRight size={18} />
          </button>

          <div className="secure-login-note">
            <ShieldCheck size={16} />
            Your session is protected and automatically expires
            for security.
          </div>
        </form>
      </section>
    </main>
  );
}

export default AdminLogin;
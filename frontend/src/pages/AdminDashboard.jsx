import { useMemo } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import { getStoredAdmin } from "../utils/adminAuth";

function AdminDashboard() {
  const navigate = useNavigate();
  const { appointments } = useOutletContext();
  const admin = getStoredAdmin();

  const counts = useMemo(() => {
    return appointments.reduce(
      (summary, appointment) => {
        summary.total += 1;

        if (summary[appointment.status] !== undefined) {
          summary[appointment.status] += 1;
        }

        return summary;
      },
      {
        total: 0,
        confirmed: 0,
        rescheduled: 0,
        on_hold: 0,
        cancelled: 0,
      }
    );
  }, [appointments]);

  const initials = (admin?.full_name || "Admin")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const cards = [
    ["Total records", counts.total, CalendarDays],
    ["Confirmed", counts.confirmed, CheckCircle2],
    ["Rescheduled", counts.rescheduled, RefreshCw],
    ["On hold", counts.on_hold, Clock3],
    ["Cancelled", counts.cancelled, XCircle],
  ];

  return (
    <div className="bank-content">
      <section className="bank-welcome-row">
        <div>
          <p className="bank-section-label">
            OPERATIONS OVERVIEW
          </p>
          <h1>
            Welcome back,{" "}
            {admin?.full_name?.split(" ")[0] ||
              "Administrator"}
          </h1>
          <p>
            Monitor appointment activity and pending actions
            from one secure workspace.
          </p>
        </div>
      </section>

      <section className="bank-admin-profile-card">
        <div className="bank-admin-profile-identity">
          <div className="bank-large-avatar">
            {initials}
          </div>

          <div>
            <span>AUTHENTICATED ADMINISTRATOR</span>
            <h2>{admin?.full_name || "Administrator"}</h2>
            <p>{admin?.email || "No email available"}</p>
          </div>
        </div>

        <div className="bank-admin-profile-meta">
          <div>
            <span>Access role</span>
            <strong>{admin?.role || "admin"}</strong>
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

          <div className="bank-session-status">
            <span>Session status</span>
            <strong>
              <i />
              Secure & active
            </strong>
          </div>
        </div>

        <button
          type="button"
          className="bank-profile-button"
          onClick={() => navigate("/admin/profile")}
        >
          View profile
          <ChevronRight size={17} />
        </button>
      </section>

      <section className="bank-stat-grid">
        {cards.map(([label, value, Icon]) => (
          <button
            type="button"
            className="bank-stat-card"
            key={label}
            onClick={() => navigate("/admin/appointments")}
          >
            <div className="bank-stat-card-top">
              <div className="bank-stat-icon">
                <Icon size={20} />
              </div>
            </div>

            <strong>{value}</strong>
            <h3>{label}</h3>
            <p>Open detailed appointment register</p>
          </button>
        ))}
      </section>

      <section className="bank-dashboard-action-grid">
        <button
          type="button"
          onClick={() => navigate("/admin/appointments")}
        >
          <CalendarDays size={20} />
          <div>
            <strong>Appointment register</strong>
            <span>Review and manage all records</span>
          </div>
          <ChevronRight size={18} />
        </button>

        <button
          type="button"
          onClick={() => navigate("/admin/customers")}
        >
          <ShieldCheck size={20} />
          <div>
            <strong>Customer directory</strong>
            <span>Open complete customer histories</span>
          </div>
          <ChevronRight size={18} />
        </button>
      </section>
    </div>
  );
}

export default AdminDashboard;

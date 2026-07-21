import { useMemo } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  CalendarClock,
  ChevronRight,
  FileClock,
  ShieldCheck,
} from "lucide-react";

function AdminAudit() {
  const navigate = useNavigate();
  const { appointments = [] } = useOutletContext();

  const recent = useMemo(
    () =>
      [...appointments]
        .sort(
          (a, b) =>
            new Date(b.updated_at || b.created_at || 0) -
            new Date(a.updated_at || a.created_at || 0)
        )
        .slice(0, 50),
    [appointments]
  );

  return (
    <div className="bank-content bank-audit-page">
      <section className="bank-page-heading bank-audit-heading">
        <div>
          <p className="bank-section-label">
            ACTIVITY REGISTER
          </p>
          <h1>Recent record activity</h1>
          <p>
            Review the latest appointment changes and open the
            related customer record.
          </p>
        </div>

        <div className="bank-audit-summary">
          <FileClock size={20} />
          <div>
            <strong>{recent.length}</strong>
            <span>Recent entries</span>
          </div>
        </div>
      </section>

      <section className="bank-table-panel bank-audit-panel">
        <div className="bank-table-header">
          <div>
            <h2>Activity timeline</h2>
            <span>
              Latest created and updated appointment records
            </span>
          </div>
        </div>

        {recent.length === 0 ? (
          <div className="bank-empty-state">
            <FileClock size={24} />
            No activity records found.
          </div>
        ) : (
          <div className="bank-audit-list">
            {recent.map((appointment) => {
              const timestamp =
                appointment.updated_at ||
                appointment.created_at;

              return (
                <article
                  className="bank-audit-row"
                  key={appointment.id}
                >
                  <div className="bank-audit-icon">
                    <CalendarClock size={19} />
                  </div>

                  <div className="bank-audit-main">
                    <div className="bank-audit-title-row">
                      <strong>
                        {appointment.appointment_code ||
                          appointment.id}
                      </strong>

                      <span
                        className={`admin-status-badge ${
                          appointment.status || "unknown"
                        }`}
                      >
                        {(appointment.status || "unknown").replace(
                          "_",
                          " "
                        )}
                      </span>
                    </div>

                    <h3>
                      {appointment.customer_name ||
                        "Unnamed customer"}
                    </h3>

                    <p>
                      Appointment record was created or updated.
                    </p>
                  </div>

                  <div className="bank-audit-meta">
                    <span>Last activity</span>
                    <strong>
                      {timestamp
                        ? new Date(timestamp).toLocaleString(
                            "en-IN"
                          )
                        : "Not available"}
                    </strong>
                  </div>

                  <button
                    type="button"
                    className="bank-audit-open"
                    disabled={!appointment.phone_number}
                    onClick={() => {
                      if (appointment.phone_number) {
                        navigate(
                          `/admin/customers/${encodeURIComponent(
                            appointment.phone_number
                          )}`
                        );
                      }
                    }}
                  >
                    Open record
                    <ChevronRight size={16} />
                  </button>
                </article>
              );
            })}
          </div>
        )}

        <div className="bank-audit-security-note">
          <ShieldCheck size={16} />
          Activity data is available only to authenticated
          administrators.
        </div>
      </section>
    </div>
  );
}

export default AdminAudit;
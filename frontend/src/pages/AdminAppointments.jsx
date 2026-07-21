import { useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { ChevronRight, Search } from "lucide-react";

function AdminAppointments() {
  const navigate = useNavigate();
  const { appointments } = useOutletContext();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  const filtered = useMemo(() => {
    const value = search.trim().toLowerCase();

    return appointments.filter((appointment) => {
      const statusMatch =
        status === "all" || appointment.status === status;

      const text = [
        appointment.appointment_code,
        appointment.customer_name,
        appointment.phone_number,
        appointment.appointment_date,
        appointment.appointment_time,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return statusMatch && (!value || text.includes(value));
    });
  }, [appointments, search, status]);

  return (
    <div className="bank-content">
      <section className="bank-page-heading">
        <div>
          <p className="bank-section-label">
            APPOINTMENT REGISTER
          </p>
          <h1>Appointments</h1>
          <p>Search, filter, and open secured records.</p>
        </div>
      </section>

      <section className="bank-table-panel">
        <div className="bank-table-header">
          <div>
            <h2>All appointment records</h2>
            <span>{filtered.length} records</span>
          </div>

          <div className="bank-table-controls">
            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value)
              }
            >
              <option value="all">All statuses</option>
              <option value="confirmed">Confirmed</option>
              <option value="rescheduled">Rescheduled</option>
              <option value="on_hold">On hold</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <div className="bank-search-box">
              <Search size={18} />
              <input
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search record"
              />
            </div>
          </div>
        </div>

        <div className="bank-table-wrapper">
          <table className="bank-appointments-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Customer</th>
                <th>Phone</th>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {filtered.map((appointment) => (
                <tr key={appointment.id}>
                  <td className="bank-record-id">
                    {appointment.appointment_code}
                  </td>
                  <td>{appointment.customer_name || "—"}</td>
                  <td>{appointment.phone_number || "—"}</td>
                  <td>{appointment.appointment_date || "—"}</td>
                  <td>{appointment.appointment_time || "—"}</td>
                  <td>
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
                  </td>
                  <td>
                    <button
                      type="button"
                      className="bank-view-button"
                      disabled={!appointment.phone_number}
                      onClick={() =>
                        navigate(
                          `/admin/customers/${encodeURIComponent(
                            appointment.phone_number
                          )}`
                        )
                      }
                    >
                      View record
                      <ChevronRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default AdminAppointments;

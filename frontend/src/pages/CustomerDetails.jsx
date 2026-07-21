import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CalendarDays,
  Edit3,
  Phone,
  RefreshCw,
  Save,
  UserRound,
  X,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

const EMPTY_FORM = {
  customer_name: "",
  phone_number: "",
  appointment_date: "",
  appointment_time: "",
  status: "confirmed",
  calendar_event_id: "",
};

function CustomerDetails() {
  const navigate = useNavigate();
  const { phoneNumber } = useParams();

  const [customer, setCustomer] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const fetchCustomer = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/customers/${encodeURIComponent(phoneNumber)}`
      );

      if (!response.ok) {
        throw new Error(`Customer API returned ${response.status}`);
      }

      const data = await response.json();
      setCustomer(data.customer || null);
      setAppointments(data.appointments || []);
    } catch (requestError) {
      console.error(requestError);
      setError("Could not load customer details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomer();
  }, [phoneNumber]);

  const counts = useMemo(() => {
    return appointments.reduce(
      (summary, appointment) => {
        summary.total += 1;
        if (summary[appointment.status] !== undefined) {
          summary[appointment.status] += 1;
        }
        return summary;
      },
      { total: 0, confirmed: 0, rescheduled: 0, cancelled: 0, on_hold: 0 }
    );
  }, [appointments]);

  const beginEdit = (appointment) => {
    setEditingAppointment(appointment);
    setFormData({
      customer_name: appointment.customer_name || "",
      phone_number: appointment.phone_number || "",
      appointment_date: appointment.appointment_date || "",
      appointment_time: appointment.appointment_time || "",
      status: appointment.status || "confirmed",
      calendar_event_id: appointment.calendar_event_id || "",
    });
    setError("");
  };

  const closeEdit = () => {
    setEditingAppointment(null);
    setFormData(EMPTY_FORM);
    setError("");
  };

  const updateField = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const saveAppointment = async (event) => {
    event.preventDefault();
    if (!editingAppointment) return;

    setSaving(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/appointments/${editingAppointment.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formData),
        }
      );

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Update API returned ${response.status}`);
      }

      closeEdit();
      await fetchCustomer();
    } catch (requestError) {
      console.error(requestError);
      setError(requestError.message || "Could not update appointment.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="admin-empty-state">Loading customer history...</div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard customer-details-page">
      <header className="customer-details-header">
        <button type="button" className="admin-back-button" onClick={() => navigate("/admin")}>
          <ArrowLeft size={18} /> Dashboard
        </button>

        <button type="button" className="admin-refresh-button" onClick={fetchCustomer}>
          <RefreshCw size={18} /> Refresh
        </button>
      </header>

      {error && <div className="admin-error-message customer-error">{error}</div>}

      <section className="customer-profile-card">
        <div className="customer-avatar"><UserRound size={34} /></div>
        <div>
          <p className="admin-eyebrow">Customer profile</p>
          <h1>{customer?.customer_name || "Unnamed customer"}</h1>
          <div className="customer-profile-meta">
            <span><Phone size={16} /> {customer?.phone_number || phoneNumber}</span>
            <span><CalendarDays size={16} /> {appointments.length} appointment{appointments.length === 1 ? "" : "s"}</span>
          </div>
        </div>
      </section>

      <section className="customer-stat-grid">
        {[
          ["Total", counts.total],
          ["Confirmed", counts.confirmed],
          ["Rescheduled", counts.rescheduled],
          ["On hold", counts.on_hold],
          ["Cancelled", counts.cancelled],
        ].map(([label, value]) => (
          <article className="customer-stat-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="admin-appointments-panel">
        <div className="admin-panel-toolbar">
          <div>
            <h2>Complete appointment history</h2>
            <p>Appointment IDs are permanent and cannot be edited.</p>
          </div>
        </div>

        {appointments.length === 0 ? (
          <div className="admin-empty-state">No appointment history found.</div>
        ) : (
          <div className="admin-table-wrapper">
            <table className="admin-appointments-table customer-history-table">
              <thead>
                <tr>
                  <th>Appointment ID</th>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appointment) => (
                  <tr key={appointment.id}>
                    <td><strong>{appointment.appointment_code}</strong></td>
                    <td>{appointment.customer_name || "Not provided"}</td>
                    <td>{appointment.phone_number || "Not provided"}</td>
                    <td>{appointment.appointment_date || "Not provided"}</td>
                    <td>{appointment.appointment_time || "Not provided"}</td>
                    <td>
                      <span className={`admin-status-badge ${appointment.status || "unknown"}`}>
                        {(appointment.status || "unknown").replace("_", " ")}
                      </span>
                    </td>
                    <td>{appointment.created_at ? new Date(appointment.created_at).toLocaleString() : "—"}</td>
                    <td>{appointment.updated_at ? new Date(appointment.updated_at).toLocaleString() : "—"}</td>
                    <td>
                      <button type="button" className="admin-edit-button" onClick={() => beginEdit(appointment)}>
                        <Edit3 size={16} /> Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editingAppointment && (
        <div className="admin-modal-backdrop">
          <form className="admin-edit-modal" onSubmit={saveAppointment}>
            <div className="admin-edit-modal-header">
              <div>
                <p className="admin-eyebrow">Edit appointment</p>
                <h2>{editingAppointment.appointment_code}</h2>
              </div>
              <button type="button" className="admin-modal-close" onClick={closeEdit} aria-label="Close">
                <X size={20} />
              </button>
            </div>

            <div className="admin-edit-grid">
              <label>
                Customer name
                <input name="customer_name" value={formData.customer_name} onChange={updateField} />
              </label>

              <label>
                Phone number
                <input name="phone_number" value={formData.phone_number} onChange={updateField} />
              </label>

              <label>
                Appointment date
                <input type="date" name="appointment_date" value={formData.appointment_date} onChange={updateField} />
              </label>

              <label>
                Appointment time
                <input type="time" step="900" name="appointment_time" value={formData.appointment_time} onChange={updateField} />
              </label>

              <label>
                Status
                <select name="status" value={formData.status} onChange={updateField}>
                  <option value="confirmed">Confirmed</option>
                  <option value="rescheduled">Rescheduled</option>
                  <option value="on_hold">On hold</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>

              <label>
                Calendar event ID
                <input name="calendar_event_id" value={formData.calendar_event_id} onChange={updateField} />
              </label>
            </div>

            <div className="admin-readonly-id">
              Appointment ID: <strong>{editingAppointment.appointment_code}</strong>
              <span>This cannot be changed.</span>
            </div>

            <div className="admin-modal-actions">
              <button type="button" className="admin-secondary-button" onClick={closeEdit}>Cancel</button>
              <button type="submit" className="admin-primary-button" disabled={saving}>
                <Save size={17} /> {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default CustomerDetails;

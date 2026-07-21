import { useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  ChevronRight,
  Search,
  UserRound,
  UsersRound,
} from "lucide-react";

function AdminCustomers() {
  const navigate = useNavigate();
  const { appointments = [] } = useOutletContext();
  const [search, setSearch] = useState("");

  const customers = useMemo(() => {
    const map = new Map();

    appointments.forEach((appointment) => {
      const phone = appointment.phone_number;

      if (!phone) {
        return;
      }

      const current = map.get(phone) || {
        phone_number: phone,
        customer_name:
          appointment.customer_name || "Unnamed customer",
        appointments: 0,
        confirmed: 0,
        on_hold: 0,
        cancelled: 0,
        latest_date: appointment.appointment_date || null,
      };

      current.appointments += 1;

      if (appointment.status === "confirmed") {
        current.confirmed += 1;
      }

      if (appointment.status === "on_hold") {
        current.on_hold += 1;
      }

      if (appointment.status === "cancelled") {
        current.cancelled += 1;
      }

      if (
        appointment.appointment_date &&
        (!current.latest_date ||
          appointment.appointment_date > current.latest_date)
      ) {
        current.latest_date = appointment.appointment_date;
      }

      map.set(phone, current);
    });

    const normalized = search.trim().toLowerCase();

    return [...map.values()]
      .filter((customer) => {
        const searchable = [
          customer.customer_name,
          customer.phone_number,
        ]
          .join(" ")
          .toLowerCase();

        return !normalized || searchable.includes(normalized);
      })
      .sort((a, b) =>
        a.customer_name.localeCompare(b.customer_name)
      );
  }, [appointments, search]);

  return (
    <div className="bank-content bank-customers-page">
      <section className="bank-page-heading bank-customers-heading">
        <div>
          <p className="bank-section-label">
            CUSTOMER DIRECTORY
          </p>
          <h1>Customers</h1>
          <p>
            Review every customer and their complete appointment
            history.
          </p>
        </div>

        <div className="bank-directory-summary">
          <UsersRound size={20} />
          <div>
            <strong>{customers.length}</strong>
            <span>Unique customers</span>
          </div>
        </div>
      </section>

      <section className="bank-table-panel bank-customer-directory-panel">
        <div className="bank-table-header bank-customer-toolbar">
          <div>
            <h2>Customer records</h2>
            <span>
              {customers.length} customer
              {customers.length === 1 ? "" : "s"} in directory
            </span>
          </div>

          <div className="bank-search-box bank-customer-search">
            <Search size={18} />
            <input
              type="search"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search by name or phone"
            />
          </div>
        </div>

        {customers.length === 0 ? (
          <div className="bank-empty-state">
            <UsersRound size={24} />
            No customer records found.
          </div>
        ) : (
          <div className="bank-customer-card-grid">
            {customers.map((customer) => {
              const initials = customer.customer_name
                .split(" ")
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();

              return (
                <article
                  className="bank-customer-card"
                  key={customer.phone_number}
                >
                  <div className="bank-customer-card-header">
                    <div className="bank-customer-avatar">
                      {initials || <UserRound size={20} />}
                    </div>

                    <div className="bank-customer-card-identity">
                      <h3>{customer.customer_name}</h3>
                      <p>{customer.phone_number}</p>
                    </div>

                    <span className="bank-customer-card-count">
                      {customer.appointments} appt.
                    </span>
                  </div>

                  <div className="bank-customer-card-stats">
                    <div>
                      <span>Confirmed</span>
                      <strong>{customer.confirmed}</strong>
                    </div>

                    <div>
                      <span>On hold</span>
                      <strong>{customer.on_hold}</strong>
                    </div>

                    <div>
                      <span>Cancelled</span>
                      <strong>{customer.cancelled}</strong>
                    </div>
                  </div>

                  <div className="bank-customer-card-footer">
                    <div>
                      <span>Latest appointment</span>
                      <strong>
                        {customer.latest_date || "Not available"}
                      </strong>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/admin/customers/${encodeURIComponent(
                            customer.phone_number
                          )}`
                        )
                      }
                    >
                      Open profile
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

export default AdminCustomers;
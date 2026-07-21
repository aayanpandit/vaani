import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Bell,
  CalendarDays,
  ChevronRight,
  CircleUserRound,
  FileClock,
  LayoutDashboard,
  LogOut,
  Menu,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";

import {
  adminFetch,
  clearAdminSession,
  getStoredAdmin,
} from "../utils/adminAuth";

const API_BASE_URL = "http://127.0.0.1:8000";

const navItems = [
  {
    to: "/admin",
    label: "Dashboard",
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: "/admin/appointments",
    label: "Appointments",
    icon: CalendarDays,
  },
  {
    to: "/admin/customers",
    label: "Customers",
    icon: UsersRound,
  },
  {
    to: "/admin/audit",
    label: "Activity register",
    icon: FileClock,
  },
  {
    to: "/admin/profile",
    label: "Admin profile",
    icon: CircleUserRound,
  },
];

function AdminLayout() {
  const navigate = useNavigate();
  const admin = getStoredAdmin();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] =
    useState(false);
  const [appointments, setAppointments] = useState([]);
  const [unreadAppointmentIds, setUnreadAppointmentIds] =
    useState([]);
  const [latestAppointmentToast, setLatestAppointmentToast] =
    useState(null);
  const initialLoadCompleteRef = useRef(false);
  const knownAppointmentIdsRef = useRef(new Set());

  const logout = () => {
    clearAdminSession();
    navigate("/admin/login", { replace: true });
  };

  useEffect(() => {
    let active = true;
    let toastTimer = null;

    const loadNotifications = async () => {
      try {
        const response = await adminFetch(
          `${API_BASE_URL}/api/v1/admin/appointments`
        );

        if (response.status === 401) {
          logout();
          return;
        }

        if (!response.ok) {
          return;
        }

        const data = await response.json();
        const nextAppointments = data.appointments || [];

        if (!active) {
          return;
        }

        const nextIds = new Set(
          nextAppointments.map((appointment) =>
            String(appointment.id)
          )
        );

        if (!initialLoadCompleteRef.current) {
          knownAppointmentIdsRef.current = nextIds;
          initialLoadCompleteRef.current = true;
          setAppointments(nextAppointments);
          return;
        }

        const newAppointments = nextAppointments.filter(
          (appointment) =>
            !knownAppointmentIdsRef.current.has(
              String(appointment.id)
            )
        );

        knownAppointmentIdsRef.current = nextIds;
        setAppointments(nextAppointments);

        if (newAppointments.length > 0) {
          const newIds = newAppointments.map((appointment) =>
            String(appointment.id)
          );

          setUnreadAppointmentIds((current) => [
            ...new Set([...newIds, ...current]),
          ]);

          const latest = newAppointments[0];
          setLatestAppointmentToast(latest);

          if (toastTimer) {
            window.clearTimeout(toastTimer);
          }

          toastTimer = window.setTimeout(() => {
            setLatestAppointmentToast(null);
          }, 7000);
        }
      } catch {
        // Keep the admin shell usable if polling temporarily fails.
      }
    };

    loadNotifications();

    const pollingTimer = window.setInterval(
      loadNotifications,
      5000
    );

    return () => {
      active = false;
      window.clearInterval(pollingTimer);

      if (toastTimer) {
        window.clearTimeout(toastTimer);
      }
    };
  }, []);


  const notifications = useMemo(
    () =>
      appointments
        .filter((appointment) =>
          unreadAppointmentIds.includes(
            String(appointment.id)
          )
        )
        .slice(0, 6),
    [appointments, unreadAppointmentIds]
  );

  const initials = (admin?.full_name || "Admin")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const currentDate = new Intl.DateTimeFormat("en-IN", {
    dateStyle: "full",
  }).format(new Date());

  return (
    <div className="bank-admin-shell">
      <aside
        className={`bank-sidebar ${
          sidebarOpen ? "open" : ""
        }`}
      >
        <div className="bank-brand">
          <div className="bank-brand-mark">
            <ShieldCheck size={24} />
          </div>

          <div>
            <strong>VAANI</strong>
            <span>Operations Console</span>
          </div>

          <button
            type="button"
            className="bank-sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="bank-nav">
          <p>MAIN MENU</p>

          {navItems.slice(0, 4).map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  isActive ? "active" : ""
                }
                onClick={() => setSidebarOpen(false)}
              >
                <Icon size={19} />
                {item.label}

                {item.to === "/admin/appointments" && (
                  <span className="bank-nav-count">
                    {appointments.length}
                  </span>
                )}
              </NavLink>
            );
          })}

          <p>ACCOUNT</p>

          {navItems.slice(4).map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? "active" : ""
                }
                onClick={() => setSidebarOpen(false)}
              >
                <Icon size={19} />
                {item.label}
              </NavLink>
            );
          })}

          <button
            type="button"
            className="bank-nav-logout"
            onClick={logout}
          >
            <LogOut size={19} />
            Secure logout
          </button>
        </nav>

        <div className="bank-security-card">
          <ShieldCheck size={18} />

          <div>
            <strong>Secure session</strong>
            <span>JWT authentication active</span>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          type="button"
          className="bank-sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        />
      )}

      <main className="bank-main">
        <header className="bank-topbar">
          <button
            type="button"
            className="bank-mobile-menu"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={22} />
          </button>

          <div className="bank-topbar-title">
            <p>Administrative Control Centre</p>
            <strong>{currentDate}</strong>
          </div>

          <div className="bank-topbar-actions">
            <div className="bank-notification-wrapper">
              <button
                type="button"
                className="bank-icon-button"
                onClick={() =>
                  setNotificationsOpen((current) => !current)
                }
                aria-label="Notifications"
              >
                <Bell size={19} />

                {notifications.length > 0 && (
                  <span>{notifications.length}</span>
                )}
              </button>

              {notificationsOpen && (
                <div className="bank-notification-panel">
                  <div className="bank-notification-header">
                    <div>
                      <strong>Notifications</strong>
                      <span>
                        {notifications.length} new appointment
                        {notifications.length === 1 ? "" : "s"}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        setNotificationsOpen(false)
                      }
                    >
                      <X size={17} />
                    </button>
                  </div>

                  {notifications.length === 0 ? (
                    <div className="bank-notification-empty">
                      No new appointment notifications.
                    </div>
                  ) : (
                    notifications.map((appointment) => (
                      <button
                        type="button"
                        className="bank-notification-item"
                        key={appointment.id}
                        onClick={() => {
                          setNotificationsOpen(false);
                          setUnreadAppointmentIds((current) =>
                            current.filter(
                              (id) =>
                                id !== String(appointment.id)
                            )
                          );

                          if (appointment.phone_number) {
                            navigate(
                              `/admin/customers/${encodeURIComponent(
                                appointment.phone_number
                              )}`
                            );
                          }
                        }}
                      >
                        <div className="bank-notification-dot-icon" />

                        <div>
                          <strong>
                            New appointment{" "}
                            {appointment.appointment_code || `#${appointment.id}`}
                          </strong>
                          <span>
                            {appointment.customer_name ||
                              "Unnamed customer"}{" "}
                            •{" "}
                            {appointment.appointment_date ||
                              "Date pending"}
                          </span>
                        </div>

                        <ChevronRight size={16} />
                      </button>
                    ))
                  )}

                  <button
                    type="button"
                    className="bank-notification-footer"
                    onClick={() => {
                      setNotificationsOpen(false);
                      navigate("/admin/appointments");
                    }}
                  >
                    View all appointments
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              className="bank-profile-trigger"
              onClick={() => navigate("/admin/profile")}
            >
              <div className="bank-profile-avatar">
                {initials}
              </div>

              <div>
                <strong>
                  {admin?.full_name || "Administrator"}
                </strong>
                <span>{admin?.role || "System Admin"}</span>
              </div>

              <ChevronRight size={17} />
            </button>
          </div>
        </header>


        {latestAppointmentToast && (
          <button
            type="button"
            className="bank-live-appointment-toast"
            onClick={() => {
              setLatestAppointmentToast(null);
              setUnreadAppointmentIds((current) =>
                current.filter(
                  (id) =>
                    id !==
                    String(latestAppointmentToast.id)
                )
              );

              if (latestAppointmentToast.phone_number) {
                navigate(
                  `/admin/customers/${encodeURIComponent(
                    latestAppointmentToast.phone_number
                  )}`
                );
              } else {
                navigate("/admin/appointments");
              }
            }}
          >
            <div className="bank-live-toast-icon">
              <Bell size={19} />
            </div>

            <div>
              <span>NEW APPOINTMENT</span>
              <strong>
                {latestAppointmentToast.customer_name ||
                  "New customer"}
              </strong>
              <p>
                {latestAppointmentToast.appointment_date ||
                  "Date pending"}{" "}
                at{" "}
                {latestAppointmentToast.appointment_time ||
                  "Time pending"}
              </p>
            </div>

            <ChevronRight size={18} />
          </button>
        )}

        <Outlet context={{ appointments, setAppointments }} />
      </main>
    </div>
  );
}

export default AdminLayout;
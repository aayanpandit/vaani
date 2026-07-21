import { CalendarDays, Phone, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

function UserLogin() {
  const navigate = useNavigate();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    const cleanNumber = phoneNumber.replace(/\D/g, "");

    if (!/^[6-9]\d{9}$/.test(cleanNumber)) {
      setError("Please enter a valid 10-digit mobile number.");
      return;
    }

    localStorage.setItem("vaani_user_phone", cleanNumber);
    navigate("/user/dashboard");
  };

  return (
    <main className="user-login-page">
      <section className="login-visual">
        <div className="user-brand">
          <div className="brand-icon">
            <Sparkles size={26} />
          </div>

          <div>
            <h1>Vaani</h1>
            <p>Your AI appointment assistant</p>
          </div>
        </div>

        <div className="visual-content">
          <span className="visual-label">Appointments made simple</span>

          <h2>
            Manage your appointments without waiting on a call.
          </h2>

          <p>
            View upcoming bookings, receive live updates and manage your
            appointments from one place.
          </p>

          <div className="visual-feature">
            <CalendarDays size={22} />

            <div>
              <strong>Always up to date</strong>
              <span>Get instant booking and schedule notifications.</span>
            </div>
          </div>
        </div>
      </section>

      <section className="login-panel">
        <form className="user-login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <span className="mobile-icon">
              <Phone size={24} />
            </span>

            <h2>View your appointments</h2>

            <p>
              Enter the mobile number you used while booking your appointment.
            </p>
          </div>

          <label htmlFor="phone">Mobile number</label>

          <div className="phone-input-wrapper">
            <span>+91</span>

            <input
              id="phone"
              type="tel"
              value={phoneNumber}
              placeholder="98765 43210"
              maxLength={14}
              onChange={(event) => {
                setPhoneNumber(event.target.value);
                setError("");
              }}
            />
          </div>

          {error && <p className="form-error">{error}</p>}

          <button className="user-primary-button" type="submit">
            Continue
          </button>

          <p className="login-note">
            We’ll use this number only to find your appointments.
          </p>
        </form>
      </section>
    </main>
  );
}

export default UserLogin;
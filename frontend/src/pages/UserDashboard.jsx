import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Delete,
  MessageCircle,
  Phone,
  Send,
  X,
} from "lucide-react";

import VoiceAssistant from "../components/VoiceAssistant";

const VAANI_NUMBER = "1707-1809-05";

const KEYPAD = [
  ["1", ""],
  ["2", "ABC"],
  ["3", "DEF"],
  ["4", "GHI"],
  ["5", "JKL"],
  ["6", "MNO"],
  ["7", "PQRS"],
  ["8", "TUV"],
  ["9", "WXYZ"],
  ["*", ""],
  ["0", "+"],
  ["#", ""],
];

function formatDialledNumber(value) {
  const digits = value.replace(/\D/g, "").slice(0, 10);

  if (digits.length <= 4) return digits;
  if (digits.length <= 8) {
    return `${digits.slice(0, 4)}-${digits.slice(4)}`;
  }

  return `${digits.slice(0, 4)}-${digits.slice(
    4,
    8
  )}-${digits.slice(8)}`;
}

function UserDashboard() {
  const [activeApp, setActiveApp] = useState("home");
  const [dialledNumber, setDialledNumber] = useState("");
  const [callStage, setCallStage] = useState("idle");
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [showThread, setShowThread] = useState(false);
  const [notification, setNotification] = useState(null);
  const [ringCount, setRingCount] = useState(1);

  useEffect(() => {
    const saved = localStorage.getItem("vaani_phone_messages");

    if (!saved) return;

    try {
      setMessages(JSON.parse(saved));
    } catch {
      setMessages([]);
    }
  }, []);

  const persistMessages = (nextMessages) => {
    setMessages(nextMessages);
    localStorage.setItem(
      "vaani_phone_messages",
      JSON.stringify(nextMessages)
    );
  };

  const addDigit = (digit) => {
    setDialledNumber((current) =>
      formatDialledNumber(`${current}${digit}`)
    );
  };

  const deleteDigit = () => {
    setDialledNumber((current) =>
      formatDialledNumber(
        current.replace(/\D/g, "").slice(0, -1)
      )
    );
  };

  const startCall = () => {
    if (dialledNumber !== VAANI_NUMBER) {
      window.alert(`Please dial ${VAANI_NUMBER} to call Vaani.`);
      return;
    }

    setCallStage("ringing");
    setRingCount(1);

    window.setTimeout(() => setRingCount(2), 950);

    window.setTimeout(() => {
      setCallStage("connected");
      setVoiceOpen(true);
    }, 1900);
  };

  const buildMessage = (appointment) => ({
    id: Date.now(),
    sender: VAANI_NUMBER,
    receivedAt: new Date().toISOString(),
    unread: true,
    body: "Your appointment has been booked successfully.",
    appointment,
  });

  const handleAppointmentBooked = (appointment) => {
    const newMessage = buildMessage(appointment);

    setMessages((current) => {
      const alreadyExists = current.some(
        (message) =>
          String(message.appointment?.id) ===
          String(appointment?.id)
      );

      if (alreadyExists) {
        return current;
      }

      const next = [newMessage, ...current];

      localStorage.setItem(
        "vaani_phone_messages",
        JSON.stringify(next)
      );

      return next;
    });

    setNotification(newMessage);

    window.setTimeout(() => {
      setNotification(null);
    }, 7000);
  };

  const handleCallClosed = () => {
    setVoiceOpen(false);
    setCallStage("idle");
    setRingCount(1);
    setDialledNumber("");
    setActiveApp("home");
  };

  const openMessages = () => {
    setActiveApp("messages");
    setShowThread(false);
  };

  const openThread = () => {
    setShowThread(true);

    const nextMessages = messages.map((message) => ({
      ...message,
      unread: false,
    }));

    persistMessages(nextMessages);
    setNotification(null);
  };

  const unreadCount = messages.filter(
    (message) => message.unread
  ).length;

  const latestMessage = messages[0];

  const currentTime = useMemo(
    () =>
      new Intl.DateTimeFormat("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date()),
    [activeApp, callStage]
  );

  return (
    <main className="phone-simulator-page">
      <section className="smartphone-shell">
        <div className="smartphone-speaker" />

        <header className="smartphone-statusbar">
          <strong>{currentTime}</strong>
          <div>
            <span>5G</span>
            <span>▮▮▮</span>
            <span className="phone-battery">82%</span>
          </div>
        </header>

        <section className="smartphone-screen">
          {notification && activeApp === "home" && (
            <button
              type="button"
              className="phone-notification-banner"
              onClick={() => {
                openMessages();
                window.setTimeout(openThread, 0);
              }}
            >
              <div className="phone-notification-icon">
                <MessageCircle size={21} />
              </div>

              <div>
                <div>
                  <strong>Vaani</strong>
                  <span>now</span>
                </div>
                <p>{notification.body}</p>
              </div>

              <button
                type="button"
                aria-label="Dismiss notification"
                onClick={(event) => {
                  event.stopPropagation();
                  setNotification(null);
                }}
              >
                <X size={16} />
              </button>
            </button>
          )}

          {activeApp === "home" && (
            <div className="phone-home-screen">
              <div className="phone-home-brand">
                <span>V</span>
                <div>
                  <strong>Vaani Connect</strong>
                  <small>Appointment calling assistant</small>
                </div>
              </div>

              <div className="phone-home-copy">
                <p>SMART APPOINTMENTS</p>
                <h1>Call Vaani. Speak naturally. Get booked.</h1>
                <span>
                  Use the phone app to call Vaani or open Messages
                  to see appointment confirmations.
                </span>
              </div>

              <div className="phone-home-apps">
                <button
                  type="button"
                  onClick={() => setActiveApp("phone")}
                >
                  <span className="home-app-icon call-app">
                    <Phone size={29} />
                  </span>
                  <strong>Phone</strong>
                </button>

                <button
                  type="button"
                  onClick={openMessages}
                >
                  <span className="home-app-icon message-app">
                    <MessageCircle size={29} />
                    {unreadCount > 0 && <i>{unreadCount}</i>}
                  </span>
                  <strong>Messages</strong>
                </button>
              </div>
            </div>
          )}

          {activeApp === "phone" && (
            <div className="phone-keypad-screen">
              <div className="phone-app-header">
                <button
                  type="button"
                  onClick={() => {
                    setActiveApp("home");
                    setDialledNumber("");
                  }}
                >
                  <ArrowLeft size={22} />
                </button>
                <strong>Phone</strong>
                <span />
              </div>

              <div className="phone-dial-contact">
                <div className="phone-dial-avatar">V</div>
                <strong>Vaani</strong>
                <span>Appointment assistant</span>
              </div>

              <div className="phone-dial-display">
                <strong>{dialledNumber || "Enter number"}</strong>
                <small>
                  {dialledNumber === VAANI_NUMBER
                    ? "Vaani Appointment Line"
                    : `Dial Vaani: ${VAANI_NUMBER}`}
                </small>
              </div>

              <div className="phone-keypad-grid">
                {KEYPAD.map(([digit, letters]) => (
                  <button
                    type="button"
                    key={digit}
                    onClick={() => addDigit(digit)}
                  >
                    <strong>{digit}</strong>
                    <small>{letters}</small>
                  </button>
                ))}
              </div>

              <div className="phone-dial-actions">
                <button
                  type="button"
                  className="phone-call-button"
                  onClick={startCall}
                  disabled={!dialledNumber}
                  aria-label="Call Vaani"
                >
                  <Phone size={27} />
                </button>

                <button
                  type="button"
                  className="phone-delete-button"
                  onClick={deleteDigit}
                  disabled={!dialledNumber}
                  aria-label="Delete digit"
                >
                  <Delete size={23} />
                </button>
              </div>
            </div>
          )}

          {callStage === "ringing" && (
            <div className="phone-ringing-overlay">
              <div className="phone-contact-avatar">V</div>
              <p>Vaani</p>
              <h2>{VAANI_NUMBER}</h2>
              <span>Ringing{".".repeat(ringCount)}</span>

              <div className="phone-ringing-pulse">
                <Phone size={27} />
              </div>
            </div>
          )}

          {activeApp === "messages" && (
            <div className="phone-messages-screen">
              <div className="phone-app-header">
                <button
                  type="button"
                  onClick={() => {
                    if (showThread) {
                      setShowThread(false);
                    } else {
                      setActiveApp("home");
                    }
                  }}
                >
                  <ArrowLeft size={22} />
                </button>

                <strong>
                  {showThread ? "Vaani" : "Messages"}
                </strong>
                <span />
              </div>

              {!showThread ? (
                <div className="phone-thread-list">
                  {latestMessage ? (
                    <button
                      type="button"
                      className="phone-thread-card"
                      onClick={openThread}
                    >
                      <div className="phone-thread-avatar">V</div>

                      <div>
                        <div>
                          <strong>{VAANI_NUMBER}</strong>
                          <time>
                            {new Date(
                              latestMessage.receivedAt
                            ).toLocaleTimeString("en-IN", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </time>
                        </div>
                        <p>{latestMessage.body}</p>
                      </div>

                      {unreadCount > 0 && (
                        <span>{unreadCount}</span>
                      )}
                    </button>
                  ) : (
                    <div className="phone-empty-messages">
                      <MessageCircle size={40} />
                      <h2>No messages yet</h2>
                      <p>
                        Your appointment confirmation will appear
                        here after the Vaani call.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="phone-message-thread">
                  <div className="phone-message-contact">
                    <div>V</div>
                    <strong>Vaani</strong>
                    <span>{VAANI_NUMBER}</span>
                  </div>

                  <div className="phone-message-bubbles">
                    {[...messages].reverse().map((message) => {
                      const appointment =
                        message.appointment || {};

                      return (
                        <article
                          className="phone-message-bubble"
                          key={message.id}
                        >
                          <p>
                            <strong>
                              Vaani Appointment Confirmation
                            </strong>
                          </p>

                          <dl>
                            <div>
                              <dt>Appointment ID</dt>
                              <dd>
                                {appointment.appointment_code ||
                                  appointment.id ||
                                  "Pending"}
                              </dd>
                            </div>
                            <div>
                              <dt>Name</dt>
                              <dd>
                                {appointment.customer_name ||
                                  "Customer"}
                              </dd>
                            </div>
                            <div>
                              <dt>Date</dt>
                              <dd>
                                {appointment.date ||
                                  appointment.appointment_date ||
                                  "Pending"}
                              </dd>
                            </div>
                            <div>
                              <dt>Time</dt>
                              <dd>
                                {appointment.time ||
                                  appointment.appointment_time ||
                                  "Pending"}
                              </dd>
                            </div>
                            <div>
                              <dt>Status</dt>
                              <dd>
                                {appointment.status ||
                                  "confirmed"}
                              </dd>
                            </div>
                          </dl>

                          <p>{message.body}</p>

                          <time>
                            {new Date(
                              message.receivedAt
                            ).toLocaleString("en-IN")}
                          </time>
                        </article>
                      );
                    })}
                  </div>

                  <div className="phone-message-composer">
                    <input
                      disabled
                      placeholder="Messages from Vaani"
                    />
                    <button type="button" disabled>
                      <Send size={18} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <div className="smartphone-home-indicator" />
      </section>

      <VoiceAssistant
        open={voiceOpen}
        onClose={handleCallClosed}
        onAppointmentBooked={handleAppointmentBooked}
        dialledNumber={VAANI_NUMBER}
      />
    </main>
  );
}

export default UserDashboard;
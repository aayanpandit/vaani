import { Grid3X3, Mic, MicOff, PhoneOff, Sparkles, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";
const RECORDING_DURATION_MS = 5000;

function VoiceAssistant({
  open,
  onClose,
  onAppointmentBooked,
  dialledNumber = "1707-1809-05",
}) {
  const audioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const isClosingRef = useRef(false);
  const sessionIdRef = useRef(`user_dashboard_${Date.now()}`);

  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("Connecting to Vaani...");
  const [error, setError] = useState("");
  const [callSeconds, setCallSeconds] = useState(0);
  const [speakerOn, setSpeakerOn] = useState(true);
  const [muted, setMuted] = useState(false);

  const [bookedAppointment, setBookedAppointment] = useState(null);
  const [bookingDetails, setBookingDetails] = useState({
  customer_name: "",
  phone_number: "",
  date: "",
  time: "",
});

  const clearRecordingTimer = () => {
    if (recordingTimerRef.current) {
      window.clearTimeout(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  };

  const stopAudio = () => {
    if (!audioRef.current) {
      return;
    }

    audioRef.current.pause();
    audioRef.current.src = "";
    audioRef.current = null;
  };

  const stopRecording = () => {
    clearRecordingTimer();

    const recorder = mediaRecorderRef.current;

    if (recorder && recorder.state === "recording") {
      try {
        recorder.stop();
      } catch (recordingError) {
        console.error("Could not stop recording:", recordingError);
      }
    }
  };

  const releaseMicrophone = () => {
    if (!mediaStreamRef.current) {
      return;
    }

    mediaStreamRef.current
      .getTracks()
      .forEach((track) => track.stop());

    mediaStreamRef.current = null;
  };

  const cleanupConversation = () => {
    clearRecordingTimer();
    stopRecording();
    stopAudio();
    releaseMicrophone();

    mediaRecorderRef.current = null;
    audioChunksRef.current = [];
  };

  const closeAssistant = () => {
    isClosingRef.current = true;
    cleanupConversation();

    setStatus("idle");
    setMessage("Connecting to Vaani...");
    setError("");

    onClose();
  };

  const playAudio = async (audioUrl, afterPlayback) => {
    stopRecording();
    stopAudio();

    setStatus("speaking");

    const fullAudioUrl = audioUrl.startsWith("http")
      ? audioUrl
      : `${API_BASE_URL}${audioUrl}`;

    const audio = new Audio(fullAudioUrl);
    audioRef.current = audio;

    audio.onended = () => {
      audioRef.current = null;

      if (!isClosingRef.current) {
        afterPlayback?.();
      }
    };

    audio.onerror = () => {
      audioRef.current = null;
      setError("I couldn't play Vaani's response.");
      setStatus("error");
    };

    try {
      await audio.play();
    } catch (playError) {
      console.error("Audio playback failed:", playError);

      setError(
        "The browser blocked audio playback. Please press Try again."
      );
      setStatus("error");
    }
  };

  const sendAudioBlob = async (audioBlob) => {
    if (isClosingRef.current) {
      return;
    }

    setStatus("thinking");
    setMessage("Processing your response...");
    setError("");

    try {
      const formData = new FormData();

      formData.append(
        "file",
        audioBlob,
        `recording-${Date.now()}.webm`
      );

      const response = await fetch(
        `${API_BASE_URL}/api/v1/voice/chat?session_id=${encodeURIComponent(
          sessionIdRef.current
        )}&current_date=${encodeURIComponent(
          new Date().toISOString().slice(0, 10)
        )}&current_time=${encodeURIComponent(
          new Date().toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
          })
        )}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();

        console.error(
          "Voice API error:",
          response.status,
          errorText
        );

        throw new Error(`Voice API returned ${response.status}`);
      }

      const data = await response.json();

      console.log("Voice response:", data);

      const assistantResponse = data.response || {};
      const extractedSession = assistantResponse.session || {};

      const latestDetails = {
        customer_name:
          extractedSession.customer_name ||
          bookingDetails.customer_name ||
          "",
        phone_number:
          extractedSession.phone_number ||
          bookingDetails.phone_number ||
          "",
        date:
          extractedSession.date ||
          bookingDetails.date ||
          "",
        time:
          extractedSession.time ||
          bookingDetails.time ||
          "",
      };

      setBookingDetails((currentDetails) => ({
        customer_name:
          extractedSession.customer_name ||
          currentDetails.customer_name,
        phone_number:
          extractedSession.phone_number ||
          currentDetails.phone_number,
        date:
          extractedSession.date ||
          currentDetails.date,
        time:
          extractedSession.time ||
          currentDetails.time,
      }));

      if (data.transcript) {
        console.log("Transcript:", data.transcript);
      }

      setMessage(
        assistantResponse.message ||
          "I didn't receive a response."
      );

      const finishConversation = () => {
        if (!assistantResponse.end_call) {
          startRecording();
          return;
        }

        releaseMicrophone();

        const bookingWasSuccessful =
          assistantResponse.status === "success" &&
          Boolean(assistantResponse.appointment_id);

        if (bookingWasSuccessful) {
          const completedAppointment = {
            id: assistantResponse.appointment_id,
            ...latestDetails,
            status: "confirmed",
          };

          setBookedAppointment(completedAppointment);
          onAppointmentBooked?.(completedAppointment);
          setStatus("completed");

          window.setTimeout(() => {
            if (!isClosingRef.current) {
              closeAssistant();
            }
          }, 1800);

          return;
        }

        if (assistantResponse.status === "on_hold") {
          setBookedAppointment(null);
          setStatus("on-hold");
          return;
        }

        setBookedAppointment(null);
        setStatus("ended");
      };

      if (assistantResponse.audio_url) {
        await playAudio(
          assistantResponse.audio_url,
          finishConversation
        );
        return;
      }

      finishConversation();
    } catch (requestError) {
      console.error("Voice request failed:", requestError);

      setError("Vaani couldn't process your voice.");
      setStatus("error");
    }
  };

  const createMediaRecorder = (stream) => {
    const supportedTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
    ];

    const supportedMimeType = supportedTypes.find((type) =>
      MediaRecorder.isTypeSupported(type)
    );

    if (supportedMimeType) {
      return new MediaRecorder(stream, {
        mimeType: supportedMimeType,
      });
    }

    return new MediaRecorder(stream);
  };

  const startRecording = async () => {
    if (isClosingRef.current) {
      return;
    }

    setError("");

    try {
      let stream = mediaStreamRef.current;

      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        mediaStreamRef.current = stream;
      }

      const recorder = createMediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.onstart = () => {
        setStatus("listening");
        setMessage("I'm listening...");
      };

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = (event) => {
        console.error("MediaRecorder error:", event);

        setError("There was a problem recording your voice.");
        setStatus("error");
      };

      recorder.onstop = async () => {
        clearRecordingTimer();

        if (isClosingRef.current) {
          audioChunksRef.current = [];
          return;
        }

        const mimeType =
          recorder.mimeType || "audio/webm";

        const audioBlob = new Blob(
          audioChunksRef.current,
          {
            type: mimeType,
          }
        );

        audioChunksRef.current = [];

        if (audioBlob.size < 1000) {
          setMessage(
            "I didn't hear anything. Listening again..."
          );

          window.setTimeout(() => {
            if (!isClosingRef.current) {
              startRecording();
            }
          }, 500);

          return;
        }

        await sendAudioBlob(audioBlob);
      };

      recorder.start();

      recordingTimerRef.current = window.setTimeout(() => {
        if (
          mediaRecorderRef.current &&
          mediaRecorderRef.current.state === "recording"
        ) {
          mediaRecorderRef.current.stop();
        }
      }, RECORDING_DURATION_MS);
    } catch (permissionError) {
      console.error(
        "Microphone permission error:",
        permissionError
      );

      if (permissionError?.name === "NotAllowedError") {
        setError(
          "Microphone permission was denied. Please allow microphone access and try again."
        );
      } else {
        setError(
          "Vaani couldn't access your microphone."
        );
      }

      setStatus("error");
    }
  };

  const fetchGreeting = async () => {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/voice/greeting`
    );

    if (!response.ok) {
      const errorText = await response.text();

      console.error(
        "Greeting API error:",
        response.status,
        errorText
      );

      throw new Error(
        `Greeting API returned ${response.status}`
      );
    }

    return response.json();
  };

  const startConversation = async () => {
    isClosingRef.current = false;

    cleanupConversation();

    setError("");
    setStatus("connecting");
    setMessage("Connecting to Vaani...");

    setBookingDetails({
  customer_name: "",
  phone_number: "",
  date: "",
  time: "",
});

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

      mediaStreamRef.current = stream;

      const greeting = await fetchGreeting();

      setMessage(
        greeting.message ||
          "Hello, Vaani this side. How may I help you?"
      );

      if (greeting.audio_url) {
        await playAudio(greeting.audio_url, () => {
          startRecording();
        });

        return;
      }

      startRecording();
    } catch (startError) {
      console.error(
        "Could not start voice conversation:",
        startError
      );

      if (startError?.name === "NotAllowedError") {
        setError(
          "Please allow microphone access so Vaani can hear you."
        );
      } else {
        setError(
          "Vaani couldn't start the conversation."
        );
      }

      setStatus("error");
    }
  };

  useEffect(() => {
    if (!open) {
      setCallSeconds(0);
      return undefined;
    }

    const timer = window.setInterval(() => {
      setCallSeconds((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [open]);

  const formattedCallTime = `${String(
    Math.floor(callSeconds / 60)
  ).padStart(2, "0")}:${String(callSeconds % 60).padStart(
    2,
    "0"
  )}`;

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    sessionIdRef.current = `user_dashboard_${Date.now()}`;
    isClosingRef.current = false;

    startConversation();

    return () => {
      isClosingRef.current = true;
      cleanupConversation();
    };
  }, [open]);

  if (!open) {
    return null;
  }

  const statusLabel = {
    connecting: "Connecting…",
    speaking: "Vaani is speaking",
    listening: "Listening…",
    thinking: "Processing…",
    completed: "Appointment booked",
    "on-hold": "Request on hold",
    ended: "Call ended",
    error: "Connection issue",
    idle: "Connecting…",
  }[status];

  return (
    <div className="active-call-overlay">
      <section className="active-call-screen simple-call-screen">
        <div className="active-call-statusbar">
          <span>{formattedCallTime}</span>
          <span>Vaani call</span>
        </div>

        <div className="simple-call-contact">
          <div className={`active-call-avatar ${status}`}>
            <Sparkles size={40} />
            <span />
            <span />
          </div>

          <h1>Vaani</h1>
          <p>{dialledNumber}</p>
          <span>{statusLabel}</span>
        </div>

        <div className="simple-call-controls">
          <button
            type="button"
            className={muted ? "active" : ""}
            onClick={() => setMuted((current) => !current)}
          >
            {muted ? <MicOff size={24} /> : <Mic size={24} />}
            <span>{muted ? "Unmute" : "Mute"}</span>
          </button>

          <button
            type="button"
            className={speakerOn ? "active" : ""}
            onClick={() => setSpeakerOn((current) => !current)}
          >
            <Volume2 size={24} />
            <span>Speaker</span>
          </button>
        </div>

        {status === "error" && (
          <button
            type="button"
            className="active-call-retry"
            onClick={startConversation}
          >
            Try again
          </button>
        )}

        <button
          type="button"
          className="active-call-end simple-hangup-button"
          onClick={closeAssistant}
          aria-label="End call"
        >
          <PhoneOff size={28} />
        </button>

        <small className="active-call-end-label">
          End call
        </small>
      </section>
    </div>
  );
}

export default VoiceAssistant;
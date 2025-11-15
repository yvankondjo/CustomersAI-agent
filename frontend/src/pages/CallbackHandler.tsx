import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

/**
 * OAuth Callback Handler
 * Handles redirect after social media OAuth flow
 */
const CallbackHandler = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Processing authentication...");

  useEffect(() => {
    // Parse URL parameters
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    // Check for errors
    if (error) {
      setStatus("error");
      setMessage(errorDescription || `Authentication failed: ${error}`);

      // Redirect back to connect page after 3 seconds
      setTimeout(() => {
        navigate("/connect");
      }, 3000);
      return;
    }

    // Check for required parameters
    if (!code || !state) {
      setStatus("error");
      setMessage("Invalid callback parameters. Missing code or state.");

      setTimeout(() => {
        navigate("/connect");
      }, 3000);
      return;
    }

    // Success - backend already handled the callback via /callback route
    // The backend endpoint processes the code and saves the account
    setStatus("success");
    setMessage("Account connected successfully!");

    // Redirect back to connect page after 2 seconds
    setTimeout(() => {
      navigate("/connect");
    }, 2000);
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="flex flex-col items-center text-center">
          {/* Icon */}
          <div className="mb-4">
            {status === "loading" && (
              <Loader2 className="h-16 w-16 text-blue-600 animate-spin" />
            )}
            {status === "success" && (
              <CheckCircle className="h-16 w-16 text-green-600" />
            )}
            {status === "error" && (
              <XCircle className="h-16 w-16 text-red-600" />
            )}
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {status === "loading" && "Connecting..."}
            {status === "success" && "Success!"}
            {status === "error" && "Error"}
          </h1>

          {/* Message */}
          <p className="text-gray-600 mb-6">{message}</p>

          {/* Loading indicator */}
          {status === "loading" && (
            <div className="text-sm text-gray-500">
              Please wait while we complete the authentication...
            </div>
          )}

          {/* Redirect message */}
          {(status === "success" || status === "error") && (
            <div className="text-sm text-gray-500">
              Redirecting to connections page...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CallbackHandler;

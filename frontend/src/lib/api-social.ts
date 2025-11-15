/**
 * API functions for social media account connections
 */

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface SocialAccount {
  id: string;
  platform: "instagram" | "whatsapp" | "messenger" | "facebook";
  account_id: string;
  account_username?: string;
  account_name?: string;
  display_name?: string;
  profile_url?: string;
  is_active: boolean;
  created_at: string;
  metadata?: {
    follower_count?: number;
    media_count?: number;
    biography?: string;
    profile_picture_url?: string;
  };
}

/**
 * Get all connected social media accounts
 */
export const getSocialAccounts = async (): Promise<SocialAccount[]> => {
  try {
    const response = await fetch(`${API_URL}/api/v1/social-accounts/`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch social accounts: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching social accounts:", error);
    return [];
  }
};

/**
 * Connect a social media platform (redirects to OAuth)
 */
export const connectPlatform = async (platform: string) => {
  try {
    const response = await fetch(`${API_URL}/api/v1/social-accounts/connect/${platform}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get authorization URL: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.authorization_url) {
      window.location.href = data.authorization_url;
    } else {
      throw new Error("No authorization URL in response");
    }
  } catch (error) {
    console.error("Error connecting platform:", error);
    throw error;
  }
};

/**
 * Disconnect a social media account
 */
export const disconnectAccount = async (accountId: string): Promise<boolean> => {
  try {
    const response = await fetch(
      `${API_URL}/api/v1/social-accounts/${accountId}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to disconnect account: ${response.statusText}`);
    }

    return true;
  } catch (error) {
    console.error("Error disconnecting account:", error);
    return false;
  }
};

/**
 * Cal.com Integration Types
 */
export interface CalConfig {
  api_key: string;
  event_type_id: number;
  timezone?: string;
}

/**
 * Save Cal.com configuration (for now, store in localStorage)
 * TODO: Create backend endpoint for persistent storage
 */
export const saveCalConfig = async (config: CalConfig): Promise<boolean> => {
  try {
    // For hackathon: store in localStorage
    localStorage.setItem("cal_config", JSON.stringify(config));
    return true;
  } catch (error) {
    console.error("Error saving Cal.com config:", error);
    return false;
  }
};

/**
 * Get Cal.com configuration
 */
export const getCalConfig = async (): Promise<CalConfig | null> => {
  try {
    // For hackathon: get from localStorage
    const stored = localStorage.getItem("cal_config");
    if (stored) {
      return JSON.parse(stored);
    }
    return null;
  } catch (error) {
    console.error("Error getting Cal.com config:", error);
    return null;
  }
};

/**
 * Remove Cal.com configuration
 */
export const removeCalConfig = async (): Promise<boolean> => {
  try {
    localStorage.removeItem("cal_config");
    return true;
  } catch (error) {
    console.error("Error removing Cal.com config:", error);
    return false;
  }
};

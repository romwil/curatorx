import type { APIRequestContext } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL || `http://127.0.0.1:${process.env.E2E_PORT || "8788"}`;

export async function resetOnboarding(request: APIRequestContext, complete = false) {
  await request.put(`${baseURL}/api/settings`, {
    data: {
      onboarding_complete: complete,
      plex_url: "",
      plex_token: "",
      plex_movie_section: complete ? "1" : "",
      plex_tv_section: complete ? "2" : "",
      radarr_url: "",
      radarr_api_key: "",
      sonarr_url: "",
      sonarr_api_key: "",
      llm_api_key: "",
      llm_base_url: "https://api.openai.com/v1",
      llm_provider: "openai",
      llm_model: "gpt-4o-mini",
      tmdb_api_key: "",
    },
  });
}

export async function completeOnboardingViaApi(request: APIRequestContext) {
  await request.put(`${baseURL}/api/persona`, {
    data: { curator_name: "Test Curator" },
  });
  await request.put(`${baseURL}/api/settings`, {
    data: {
      onboarding_complete: true,
      llm_provider: "openai",
      llm_model: "gpt-4o-mini",
      llm_base_url: "https://api.openai.com/v1",
      plex_url: "http://plex.local",
      plex_movie_section: "1",
      plex_tv_section: "2",
      radarr_url: "http://radarr.local",
      sonarr_url: "http://sonarr.local",
    },
  });
}

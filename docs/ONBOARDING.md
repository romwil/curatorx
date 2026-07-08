# Onboarding

1. Deploy MediaCurator (Docker/Unraid) and open port **8788**.
2. Go to **Settings** (`/config`).
3. Enter Plex URL/token and test connection. Pick movie and TV library keys.
4. Add Radarr and Sonarr credentials if you want add-to-queue actions.
5. Add a TMDB API key ([themoviedb.org](https://www.themoviedb.org/settings/api)).
6. Configure your LLM provider (BYOP) or use Ollama locally.
7. Optionally add Fanart.tv and Tautulli.
8. Save settings and return to the chat UI.
9. Click **Sync library** to index Plex metadata and build RAG embeddings.
10. Start curating — ask about genres, gaps, what to watch, or what to purge.

## Example prompts

- "I love 70s paranoid thrillers — what's missing from my collection?"
- "Show me hidden gems in sci-fi I don't own yet."
- "What should we watch tonight under 2 hours?"
- "Which large files have never been watched?"
- "Explore neo-noir with me based on what I already love."

"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

const GITHUB_STARS_STALE_TIME_MS = 3_600_000;
const TRAILING_ZERO = /\.0$/;

const repositorySchema = z.object({ stargazers_count: z.number().int().nonnegative() });

function repositorySlug(githubUrl: string): string | null {
  const slug = new URL(githubUrl).pathname.replace(/^\/+|\/+$/g, "");

  return slug.split("/").length === 2 ? slug : null;
}

async function fetchGithubStars(githubUrl: string): Promise<number | null> {
  const slug = repositorySlug(githubUrl);

  if (slug === null) {
    return null;
  }

  const response = await fetch(`https://api.github.com/repos/${slug}`);

  if (!response.ok) {
    return null;
  }

  return repositorySchema.parse(await response.json()).stargazers_count;
}

export function formatStars(stars: number): string {
  if (stars < 1000) {
    return String(stars);
  }

  return `${(stars / 1000).toFixed(1).replace(TRAILING_ZERO, "")}k`;
}

export function useGithubStars(githubUrl: string) {
  return useQuery({
    queryKey: ["github-stars", githubUrl],
    queryFn: () => {
      return fetchGithubStars(githubUrl);
    },
    staleTime: GITHUB_STARS_STALE_TIME_MS,
    retry: false,
  });
}

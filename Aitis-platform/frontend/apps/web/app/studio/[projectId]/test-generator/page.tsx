"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

/**
 * The standalone Test Generator has been merged into the Test Case Generator
 * (the former "Test Cases" tab). This route redirects there for backward
 * compatibility with old links and bookmarks.
 */
export default function TestGeneratorRedirect() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  useEffect(() => {
    router.replace(`/studio/${projectId}/test-cases`);
  }, [projectId, router]);

  return null;
}

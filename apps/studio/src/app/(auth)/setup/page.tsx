import { redirect } from "next/navigation";
import { fetchServerAuthStatus } from "@/entities/session/index.server";
import { SetupOwnerPage } from "@/_pages/setup-owner";

export default async function SetupRoute() {
  if (!(await fetchServerAuthStatus()).requires_setup) {
    redirect("/login");
  }

  return <SetupOwnerPage />;
}

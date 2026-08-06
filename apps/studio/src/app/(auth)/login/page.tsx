import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { fetchServerAuthStatus, fetchServerSessionUser } from "@/entities/session/index.server";
import { SignInPage } from "@/_pages/sign-in";

export default async function LoginRoute() {
  const cookieStore = await cookies();

  if ((await fetchServerSessionUser(cookieStore.toString())) !== null) {
    redirect("/");
  }

  if ((await fetchServerAuthStatus()).requires_setup) {
    redirect("/setup");
  }

  return <SignInPage />;
}

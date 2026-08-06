"use client";

import logomark from "@looksee/brand/logomark.svg";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { type FormEventHandler, useState } from "react";
import { Button } from "@/shared/ui/button";
import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Spinner } from "@/shared/ui/spinner";
import { useLogin } from "@/entities/session";

export function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin({
    onSuccess: () => {
      router.push("/");
      router.refresh();
    },
  });

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-2 text-center">
        <Image alt="LookSee" className="size-10" src={logomark} />

        <h1 className="font-semibold text-xl">Sign in to LookSee</h1>
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <Field>
          <FieldLabel htmlFor="login-email">Email</FieldLabel>

          <Input
            autoComplete="email"
            autoFocus
            id="login-email"
            onChange={(event) => {
              setEmail(event.currentTarget.value);
            }}
            required
            type="email"
            value={email}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="login-password">Password</FieldLabel>

          <Input
            autoComplete="current-password"
            id="login-password"
            onChange={(event) => {
              setPassword(event.currentTarget.value);
            }}
            required
            type="password"
            value={password}
          />
        </Field>

        {login.isError ? <p className="text-destructive text-sm">{login.error.message}</p> : null}

        <Button disabled={login.isPending} type="submit">
          {login.isPending ? <Spinner /> : null}
          Sign in
        </Button>
      </form>
    </div>
  );
}

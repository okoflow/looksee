"use client";

import logomark from "@looksee/brand/logomark.svg";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { type FormEventHandler, useState } from "react";
import { Button } from "@/shared/ui/button";
import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Spinner } from "@/shared/ui/spinner";
import { setupSchema, useSetupOwner } from "@/entities/session";

export function SetupOwnerPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const setup = useSetupOwner({
    onSuccess: () => {
      router.push("/");
      router.refresh();
    },
  });

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    const input = setupSchema.safeParse({ name, email, password });

    if (!input.success) {
      setValidationError(input.error.issues[0]?.message ?? "Check the form fields");

      return;
    }

    setValidationError(null);
    setup.mutate(input.data);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col items-center gap-2 text-center">
        <Image alt="LookSee" className="size-10" src={logomark} />

        <h1 className="font-semibold text-xl">Set up LookSee</h1>

        <p className="text-muted-foreground text-sm">
          Create the owner account for this instance. Until it exists, anyone who can reach this page can claim
          ownership.
        </p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <Field>
          <FieldLabel htmlFor="setup-name">Name</FieldLabel>

          <Input
            autoComplete="name"
            autoFocus
            id="setup-name"
            maxLength={128}
            onChange={(event) => {
              setName(event.currentTarget.value);
            }}
            required
            value={name}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="setup-email">Email</FieldLabel>

          <Input
            autoComplete="email"
            id="setup-email"
            onChange={(event) => {
              setEmail(event.currentTarget.value);
            }}
            required
            type="email"
            value={email}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="setup-password">Password</FieldLabel>

          <Input
            autoComplete="new-password"
            id="setup-password"
            minLength={8}
            onChange={(event) => {
              setPassword(event.currentTarget.value);
            }}
            required
            type="password"
            value={password}
          />

          <FieldDescription>At least 8 characters with one number and one capital letter.</FieldDescription>
        </Field>

        {validationError === null ? null : <p className="text-destructive text-sm">{validationError}</p>}

        {setup.isError ? <p className="text-destructive text-sm">{setup.error.message}</p> : null}

        <Button disabled={setup.isPending} type="submit">
          {setup.isPending ? <Spinner /> : null}
          Create owner account
        </Button>
      </form>
    </div>
  );
}

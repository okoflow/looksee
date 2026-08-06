"use client";

import { type FormEventHandler, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Switch } from "@/shared/ui/switch";
import { type Credential, useUpdateCredential } from "@/entities/credential";
import { buildPayload, emptyPayloadDraft } from "../config/payload-fields";
import { PayloadFields } from "./payload-fields";

interface EditCredentialDialogProps {
  credential: Credential;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function EditCredentialDialog({ credential, onOpenChange, open }: EditCredentialDialogProps) {
  const [name, setName] = useState(credential.name);
  const [replaceSecret, setReplaceSecret] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    return emptyPayloadDraft(credential.type);
  });

  const updateCredential = useUpdateCredential(credential.id, {
    onSuccess: (updated) => {
      toast.success(`Saved ${updated.name}`);

      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setName(credential.name);
      setReplaceSecret(false);
      setDraft(emptyPayloadDraft(credential.type));
    }

    onOpenChange(nextOpen);
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    updateCredential.mutate({
      name: name.trim(),
      ...(replaceSecret ? { payload: buildPayload(credential.type, draft) } : {}),
    });
  };

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit credential</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Field>
            <FieldLabel htmlFor="credential-edit-name">Name</FieldLabel>

            <Input
              id="credential-edit-name"
              maxLength={128}
              onChange={(event) => {
                setName(event.currentTarget.value);
              }}
              required
              value={name}
            />
          </Field>

          <Field orientation="horizontal">
            <FieldLabel htmlFor="credential-edit-replace">Replace stored secret</FieldLabel>

            <Switch checked={replaceSecret} id="credential-edit-replace" onCheckedChange={setReplaceSecret} />
          </Field>

          {replaceSecret ? (
            <PayloadFields draft={draft} idPrefix="credential-edit" onChange={setDraft} type={credential.type} />
          ) : (
            <FieldDescription>The stored secret is write-only; it stays unchanged unless replaced.</FieldDescription>
          )}

          <DialogFooter>
            <Button
              onClick={() => {
                onOpenChange(false);
              }}
              type="button"
              variant="outline"
            >
              Cancel
            </Button>

            <Button disabled={updateCredential.isPending} type="submit">
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

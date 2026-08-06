"use client";

import { type FormEventHandler, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { Field, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import {
  CREDENTIAL_TYPE_LABELS,
  type CredentialType,
  credentialTypeSchema,
  useCreateCredential,
} from "@/entities/credential";
import { buildPayload, emptyPayloadDraft } from "../config/payload-fields";
import { PayloadFields } from "./payload-fields";

const TYPE_OPTIONS = credentialTypeSchema.options.map((value) => {
  return { value, label: CREDENTIAL_TYPE_LABELS[value] };
});

interface CreateCredentialDialogProps {
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function CreateCredentialDialog({ onOpenChange, open }: CreateCredentialDialogProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState<CredentialType>("telegram_bot");
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    return emptyPayloadDraft("telegram_bot");
  });

  const createCredential = useCreateCredential({
    onSuccess: (credential) => {
      toast.success(`Created ${credential.name}`);

      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const resetDraft = (nextType: CredentialType) => {
    setType(nextType);
    setDraft(emptyPayloadDraft(nextType));
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setName("");
      resetDraft("telegram_bot");
    }

    onOpenChange(nextOpen);
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    createCredential.mutate({ name: name.trim(), type, payload: buildPayload(type, draft) });
  };

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New credential</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Field>
            <FieldLabel htmlFor="credential-name">Name</FieldLabel>

            <Input
              autoFocus
              id="credential-name"
              maxLength={128}
              onChange={(event) => {
                setName(event.currentTarget.value);
              }}
              placeholder="Production Slack"
              required
              value={name}
            />
          </Field>

          <Field>
            <FieldLabel htmlFor="credential-type">Type</FieldLabel>

            <Select
              items={TYPE_OPTIONS}
              onValueChange={(value: CredentialType | null) => {
                if (value !== null) {
                  resetDraft(value);
                }
              }}
              value={type}
            >
              <SelectTrigger className="w-full" id="credential-type">
                <SelectValue />
              </SelectTrigger>

              <SelectContent>
                {TYPE_OPTIONS.map((option) => {
                  return (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </Field>

          <PayloadFields draft={draft} idPrefix="credential-create" onChange={setDraft} type={type} />

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

            <Button disabled={createCredential.isPending} type="submit">
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

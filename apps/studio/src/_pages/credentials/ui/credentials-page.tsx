"use client";

import { PlusIcon } from "lucide-react";
import { type PropsWithChildren, useState } from "react";
import { Button } from "@/shared/ui/button";
import { SidebarTrigger } from "@/shared/ui/sidebar";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { useCredentials } from "@/entities/credential";
import { CreateCredentialDialog } from "@/features/credentials/manage-credentials";
import { CredentialRow } from "./credential-row";

function MessageRow({ children }: PropsWithChildren) {
  return (
    <TableRow>
      <TableCell className="py-8 text-center text-muted-foreground" colSpan={4}>
        {children}
      </TableCell>
    </TableRow>
  );
}

function CredentialRows() {
  const credentials = useCredentials();

  if (credentials.isPending) {
    return <MessageRow>Loading…</MessageRow>;
  }

  if (credentials.isError) {
    return <MessageRow>Couldn't load credentials.</MessageRow>;
  }

  if (!credentials.data.length) {
    return (
      <MessageRow>
        No credentials yet. Create one so Telegram, Slack, Discord, email, and MQTT actions can deliver.
      </MessageRow>
    );
  }

  return credentials.data.map((credential) => {
    return <CredentialRow credential={credential} key={credential.id} />;
  });
}

export function CredentialsPage() {
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="flex flex-col">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
        <SidebarTrigger className="-ml-1" />

        <h1 className="font-medium text-sm">Credentials</h1>

        <div className="ml-auto">
          <Button
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            <PlusIcon data-icon="inline-start" />
            New credential
          </Button>
        </div>
      </header>

      <div className="p-4">
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>

                <TableHead>Type</TableHead>

                <TableHead>Details</TableHead>

                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              <CredentialRows />
            </TableBody>
          </Table>
        </div>
      </div>

      <CreateCredentialDialog onOpenChange={setCreateOpen} open={createOpen} />
    </div>
  );
}

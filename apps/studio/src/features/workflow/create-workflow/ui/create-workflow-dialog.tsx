"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { workflowRoute } from "@/shared/routes";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/shared/ui/dialog";
import {
  useCreateWorkflow,
  useWorkflows,
  type WorkflowGraph,
  type WorkflowSetup,
  workflowSetupSchema,
} from "@/entities/workflow";
import { type PresetParams, presetDefaults, type WorkflowPreset } from "../config/presets";
import { resolvePresetParams } from "../lib/preset-params";
import { uniqueName } from "../lib/unique-name";
import { PresetGalleryStep } from "./preset-gallery-step";
import { WorkflowSetupStep } from "./workflow-setup-step";

const EMPTY_GRAPH: WorkflowGraph = { nodes: [], edges: [] };

const workflowSetupDefaults: WorkflowSetup = {
  name: "",
  description: "",
};

type DialogStep = "gallery" | "setup";

export function CreateWorkflowDialog() {
  const router = useRouter();

  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<DialogStep>("gallery");
  const [preset, setPreset] = useState<WorkflowPreset | null>(null);
  const [params, setParams] = useState<PresetParams>({});

  const { data: existingWorkflows } = useWorkflows();
  const createWorkflow = useCreateWorkflow({
    onSuccess: (created) => {
      toast.success("Workflow created");

      handleOpenChange(false);

      router.push(workflowRoute(created.id));
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const form = useForm<WorkflowSetup>({
    resolver: zodResolver(workflowSetupSchema),
    defaultValues: workflowSetupDefaults,
  });

  const handleOpenChange = (next: boolean) => {
    setIsOpen(next);
    setStep("gallery");
    setPreset(null);

    form.reset(workflowSetupDefaults);
  };

  const handleSelectPreset = (next: WorkflowPreset | null) => {
    const takenNames = new Set(
      (existingWorkflows ?? []).map((workflow) => {
        return workflow.name;
      })
    );

    setPreset(next);
    setParams(next === null ? {} : presetDefaults(next));
    setStep("setup");

    form.reset({
      name: next === null ? "" : uniqueName(next.defaultName, takenNames),
      description: next === null ? "" : next.description,
    });
  };

  const handleParamChange = (key: string, value: string) => {
    setParams((previous) => {
      return { ...previous, [key]: value };
    });
  };

  const handleBackToGallery = () => {
    setStep("gallery");
  };

  const handleCreate = (values: WorkflowSetup) => {
    createWorkflow.mutate({
      ...values,
      graph: preset === null ? EMPTY_GRAPH : preset.buildGraph(resolvePresetParams(preset, params)),
    });
  };

  return (
    <Dialog onOpenChange={handleOpenChange} open={isOpen}>
      <DialogTrigger render={<Button />}>
        <PlusIcon data-icon="inline-start" />
        New workflow
      </DialogTrigger>

      <DialogContent className="sm:max-w-xl">
        {step === "gallery" ? (
          <PresetGalleryStep onSelectPreset={handleSelectPreset} />
        ) : (
          <WorkflowSetupStep
            form={form}
            isPending={createWorkflow.isPending}
            onBack={handleBackToGallery}
            onParamChange={handleParamChange}
            onSubmit={handleCreate}
            params={params}
            preset={preset}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

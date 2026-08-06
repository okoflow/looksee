import { WorkflowEditorPage } from "@/_pages/workflow-editor";

interface Params {
  params: Promise<{ id: string }>;
}

export default async function WorkflowEditorRoute({ params }: Params) {
  const { id } = await params;

  return <WorkflowEditorPage id={id} />;
}

import { WorkflowMonitorPage } from "@/_pages/workflow-monitor";

interface Params {
  params: Promise<{ id: string }>;
}

export default async function WorkflowMonitorRoute({ params }: Params) {
  const { id } = await params;

  return <WorkflowMonitorPage id={id} />;
}

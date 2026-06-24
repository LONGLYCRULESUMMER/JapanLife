import { AdminShell } from "@/components/shell/admin-shell";
import { KnowledgeAdmin } from "@/components/knowledge/knowledge-admin";

export const metadata = {
  title: "Knowledge Admin",
};

export default function KnowledgeAdminPage() {
  return (
    <AdminShell>
      <KnowledgeAdmin />
    </AdminShell>
  );
}

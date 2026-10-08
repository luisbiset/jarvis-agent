import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiError, api } from '../../services/api';
import type { Operation, OperationProposal } from '../../types/api';
import { OperationWorkspace } from './OperationWorkspace';

export function OperationLauncher() {
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const operations = useQuery({ queryKey: ['operations'], queryFn: api.operations });
  const projectId = projects.data?.active_project_id || '';
  const [selected, setSelected] = useState<Operation>(); const [parameters, setParameters] = useState<Record<string, string>>({}); const [proposal, setProposal] = useState<OperationProposal>(); const [error, setError] = useState<string>(); const [pending, setPending] = useState(false);
  const preview = async () => { if (!selected || !projectId) return; setPending(true); setError(undefined); try { setProposal(await api.previewOperation(selected.operation_id, projectId, parameters)); } catch (value) { setError(value instanceof Error ? value.message : 'Não foi possível gerar a proposta.'); } finally { setPending(false); } };
  const execute = async () => { if (!proposal) return; setPending(true); setError(undefined); try { setProposal(await api.executeOperation(proposal)); } catch (value) { if (value instanceof ApiError && value.status === 409) { setProposal(undefined); setError('Esta proposta já foi executada ou expirou. Gere uma nova proposta para continuar.'); } else { setError(value instanceof Error ? value.message : 'Não foi possível iniciar a operação.'); } } finally { setPending(false); } };
  return <OperationWorkspace operations={operations.data?.operations || []} selected={selected} parameters={parameters} proposal={proposal} pending={pending} error={error} onSelect={(operation) => { setSelected(operation); setProposal(undefined); setParameters({}); }} onChange={(key, value) => setParameters((current) => ({ ...current, [key]: value }))} onPreview={preview} onExecute={execute} />;
}

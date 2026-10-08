import type { Project } from '../../types/api';

type Props = { title: string; description: string; project?: Project };

export function ModulePage({ title, description, project }: Props) {
  return <section className="mx-auto grid max-w-5xl gap-5 px-4 pb-10 sm:px-6 lg:px-12"><div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><div className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-500">{project?.name || 'Projeto não selecionado'}</div><h2 className="mt-2 text-2xl font-bold text-slate-900">{title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{description}</p></div><div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-10 text-center"><div className="text-sm font-semibold text-slate-700">Nenhum dado disponível ainda</div><p className="mt-2 text-sm text-slate-500">Este módulo exibirá dados reais do projeto ativo quando houver registros no Runtime.</p></div></section>;
}

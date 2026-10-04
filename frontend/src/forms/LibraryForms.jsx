import { useState } from 'react';
import { energies, experiences, Field, SelectField } from '../components/UI.jsx';

export function GameForm({game, onSave, onCancel, busy}) {
  const [values, setValues] = useState(game ? {...game} : {title:'', current_interest:3, friction:0, energy_required:'medium', social_mode:'solo', experience_tags:['progression'], notes:''});
  const change = (key, value) => setValues(previous => ({...previous, [key]:value}));
  function submit(event) {
    event.preventDefault();
    const {title, current_interest, friction, energy_required, social_mode, experience_tags, notes} = values;
    onSave({title, current_interest, friction, energy_required, social_mode, experience_tags, notes:notes || null}, game?.id);
  }
  return <form className="editor" onSubmit={submit} aria-label={game ? 'Edit game' : 'Add game'}><h2>{game ? 'Edit game' : 'Add a game'}</h2><fieldset disabled={busy}>
    <Field label="Game title"><input required maxLength="200" value={values.title} onChange={e => change('title', e.target.value)}/></Field>
    <div className="form-row"><SelectField label="Current interest" value={values.current_interest} onChange={v => change('current_interest', Number(v))} options={[[1,'1 · Not drawn to it'],[2,'2 · Slight interest'],[3,'3 · Interested'],[4,'4 · Keen to play'],[5,'5 · Can’t wait']]}/>
    <SelectField label="Setup friction" value={values.friction} onChange={v => change('friction', Number(v))} options={[[0,'0 · Jump right in'],[1,'1 · Very little'],[2,'2 · Some setup'],[3,'3 · Moderate effort'],[4,'4 · A lot to arrange'],[5,'5 · Hard to get going']]}/></div>
    <div className="form-row"><SelectField label="Energy required" value={values.energy_required} onChange={v => change('energy_required',v)} options={energies}/><SelectField label="Play style" value={values.social_mode} onChange={v => change('social_mode',v)} options={ [['solo','Solo'],['social','Social'],['both','Solo or social']] }/></div>
    <fieldset className="tag-options"><legend>Experiences <small>Choose at least one</small></legend>{experiences.map(([tag,label]) => <label key={tag}><input type="checkbox" checked={values.experience_tags.includes(tag)} onChange={e => change('experience_tags', e.target.checked ? [...values.experience_tags,tag] : values.experience_tags.filter(value => value !== tag))}/>{label}</label>)}</fieldset>
    <Field label="Game notes"><textarea rows="2" value={values.notes || ''} onChange={e => change('notes', e.target.value)}/></Field>
  </fieldset>{!values.experience_tags.length && <p role="alert">Choose at least one experience.</p>}<div className="actions"><button className="primary" disabled={busy || !values.experience_tags.length}>{busy ? 'Saving…' : 'Save game'}</button><button type="button" disabled={busy} onClick={onCancel}>Cancel</button></div></form>;
}

export function GoalForm({goal, gameId, onSave, onCancel, busy}) {
  const [values, setValues] = useState(goal ? {...goal} : {title:'', estimated_minutes:30, priority:2, notes:''});
  const change = (key, value) => setValues(previous => ({...previous,[key]:value}));
  function submit(event) {
    event.preventDefault();
    const {title, estimated_minutes, priority, notes} = values;
    onSave({title, estimated_minutes, priority, notes:notes || null, ...(!goal ? {game_id:gameId} : {})}, goal?.id);
  }
  return <form className="editor" aria-label={goal ? 'Edit goal' : 'Add goal'} onSubmit={submit}><h3>{goal ? 'Edit quest' : 'Add a quest'}</h3><fieldset disabled={busy}>
    <Field label="Goal title"><input required maxLength="200" value={values.title} onChange={e => change('title',e.target.value)}/></Field>
    <div className="form-row"><Field label="Estimated minutes" hint="A useful session chunk, not total completion time."><input type="number" min="1" step="1" required value={values.estimated_minutes} onChange={e => change('estimated_minutes',e.target.value === '' ? '' : Number(e.target.value))}/></Field><SelectField label="Goal priority" value={values.priority} onChange={v => change('priority',Number(v))} options={[[1,'1 · Whenever'],[2,'2 · Worth doing'],[3,'3 · Top priority']]}/></div>
    <Field label="Goal notes"><textarea rows="2" value={values.notes || ''} onChange={e => change('notes',e.target.value)}/></Field>
  </fieldset><div className="actions"><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save goal'}</button><button type="button" disabled={busy} onClick={onCancel}>Cancel</button></div></form>;
}

# Compiled UI source excerpts

The supplied repository contains minified build assets without frontend source maps. Offsets below identify the exact evidence in the supplied bytes.

## Duty-cycle display combines budget use and configured limit

- File: `repeater/web/html/assets/index-DULnzgZb.js`
- Byte offset: `50884`

```javascript
e.value>0?(s(),E(`span`,sn,`Pen: `+d(xe.value),1)):b(``,!0)]),l(y).dutyCycleEnabled?(s(),E(`div`,cn,[T(`div`,ln,[r[6]||=T(`span`,null,`Duty Cycle`,-1),T(`span`,un,d(l(y).dutyCycleUtilization.toFixed(1))+`% / `+d(l(y).dutyCycleMax.toFixed(1))+`% `,1)]),T(`div`,dn,[T(`div`,{class:`h-full rounded-full transition-all duration-300`,style:m(Te.value)},null,4)])])):b(``,!0),x(qt)]),T(`div`,fn,[(s(),E(w,null,n(we,e=>T(`button`,{key:e.id,type:`button`,title:e.title,disabled:G.value,onClick:t=>se(e.id),class:g([`flex-1 py-2 text-xs font-medium transition-all duration-200 border-r bord
```

## Radio form expects a flat backend payload

- File: `repeater/web/html/assets/Configuration-gqXY-Aef.js`
- Byte offset: `9363`

```javascript
uency=L.value*1e6),z.value&&(t.spreading_factor=z.value),B.value&&(t.bandwidth=B.value*1e3),(W.value||W.value===0)&&(t.tx_power=W.value),G.value&&(t.coding_rate=G.value);let n=(await R.post(`/update_radio_config`,t)).data;if(n.message||n.persisted)return b.value=!1,F.value=!1,await u.fetchStats(),d.invalidate(`radioConfig`),e||(E.value=!0),!0;n.error?T.value=n.error:T.value=`Unknown response from server`}catch(e){console.error(`Failed to update radio settings:`,e),T.value=e.response?.data?.error||`Failed to update settings`}finally{w.value=!1}return!1},ct=y(()=>W.value!==I.value),lt=async({silent:e=!1}={})=>b.value&&ct.v
```

## Duty-cycle form expects a flat backend payload

- File: `repeater/web/html/assets/Configuration-gqXY-Aef.js`
- Byte offset: `56056`

```javascript
handleDiscard:O,handleSave:k,handleCancel:A}=pe(d,f,w,async()=>(await M(),!d.value));t({requestLeave:E,isEditing:d});let M=async()=>{f.value=!0,m.value=``,p.value=``;try{let e=(await R.post(`/update_duty_cycle_config`,{max_airtime_percent:h.value,enforcement_enabled:g.value})).data;e?.message||e?.persisted?(p.value=e?.message||`Settings saved successfully`,d.value=!1,await n.fetchStats(),setTimeout(()=>{p.value=``},3e3)):m.value=e?.error||`Failed to save settings`}catch(e){console.error(`Failed to save duty cycle settings:`,e),m.value=e.response?.data?.error||`Failed to save settings`}finally{f.value=!1}};return(e,t)=>(a(),C(x,null,[v(fe,{show:c(T),"is-saving":f.value,label:`Dut
```

## Advert form checks success on the Axios response object

- File: `repeater/web/html/assets/Configuration-gqXY-Aef.js`
- Byte offset: `131437`

```javascript
alue,max_penalty_seconds:q.value*3600,adaptive_enabled:ne.value,ewma_alpha:re.value,hysteresis_seconds:ie.value*60,quiet_max:J.value,normal_max:Y.value,busy_max:X.value},t=await R.post(`/update_advert_rate_limit_config`,e),n=t.data;t.success?(k.value=n?.message||`Settings saved successfully`,await s.fetchStats(),await Z(),await E(),Q(),T.value=!1,setTimeout(()=>{k.value=``},3e3)):(M.value=n?.error||`Failed to save settings`,console.error(`[AdvertSettings] Save failed:`,n?.error))}catch(e){console.error(`Failed to save advert settings:`,e),M.value=e.response?.data?.error||`Failed to save settings`}finally{O.value=!1
```

## Terminal checks success on the Axios response object

- File: `repeater/web/html/assets/Terminal-CtqWeLbu.js`
- Byte offset: `549287`

```javascript
default:a(),this.writeError(e,`Unknown parameter: ${r}`),this.writeLine(e,``),this.writeInfo(e,`Type "set" without arguments to see available parameters`),n();return}a();let o=t.data||t;t.success?(o.applied&&o.applied.length>0?this.writeSuccess(e,`Configuration updated: ${o.applied.join(`, `)}`):this.writeSuccess(e,`Configuration updated`),g().fetchStats(),o.restart_required?(this.writeLine(e,``),this.writeWarning(e,`⚠ Service restart required for changes to take effect`),this.writeInfo(e,`Run: sudo systemctl restart openhop-repeater`)):o.message&&!o.live_update&&(this.
```

## Terminal fabricates persistence for quick controls

- File: `repeater/web/html/assets/Terminal-CtqWeLbu.js`
- Byte offset: `547231`

```javascript
  \x1B[36mno_tx\x1B[0m    - No repeat, no local TX; adverts skipped`),n();return}t=await h.post(`/set_mode`,{mode:r},{timeout:3e4}),t.data&&(t.data.applied=[`mode=${r}`],t.data.persisted=!0,t.data.live_update=!0);break}case`duty`:{let r=i.toLowerCase();if(r!==`on`&&r!==`off`){a(),this.writeError(e,`Duty cycle must be "on" or "off"`),this.writeLine(e,``),this.writeInfo(e,`Valid values:`),this.writeLine(e,`  \x1B[36mon\x1B[0m   - Enable duty cycle enforcement`),this.writeLine(e,`  \x1B[36moff\x1B[0m  - Disable duty cycle enforcement`),n();return}let o=r===`on`;t=await h.post(`/set_duty_
```

## Advert UI sends the documented threshold keys

- File: `repeater/web/html/assets/Configuration-gqXY-Aef.js`
- Byte offset: `131382`

```javascript
se_penalty_seconds:K.value*3600,penalty_multiplier:te.value,max_penalty_seconds:q.value*3600,adaptive_enabled:ne.value,ewma_alpha:re.value,hysteresis_seconds:ie.value*60,quiet_max:J.value,normal_max:Y.value,busy_max:X.value},t=await R.post(`/update_advert_rate_limit_config`,e),n=t.data;t.success?(k.value=n?.message||`Settings saved successfully`,await s.fetchStats(),await Z(),await E(),Q(),T.value=!1,setTimeout(()=>{k.value=``},3e3)):(M.value=n?.error||`Failed to save settings`,console.error(`[AdvertSettings] Save failed:`,n?.error))}catch(e){console.error(`Failed to save advert settings:`,e),M.v
```

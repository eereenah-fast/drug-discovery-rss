import test from 'node:test';
import assert from 'node:assert/strict';
import { effectiveDate, filterItems, type Item, type Filters } from '../lib/feed.ts';
const filters: Filters = {query:'',kind:'All',subject:'All',method:'All',period:'14',code:false,savedOnly:false};
const base: Item = {id:'paper',title:'Antibody design with a language model',url:'https://example.org',published:'2026-09-22',source:'Journal',kind:'Journals',subjects:['Antibodies'],methods:['Generative design'],first_seen:'2026-09-23T08:00:00Z',last_seen:'2026-09-23T08:00:00Z',relevance:80};
test('future issue dates and missing dates use discovery date', () => {
  assert.equal(effectiveDate({...base,published:'2027-01-01'}),'2026-09-23');
  assert.equal(effectiveDate({...base,published:null}),'2026-09-23');
});
test('search combines words and intersects source and subject filters', () => {
  assert.equal(filterItems([base],{...filters,query:'antibody model',subject:'Antibodies'},[],'2026-09-23').length,1);
  assert.equal(filterItems([base],{...filters,kind:'Code'},[],'2026-09-23').length,0);
});
test('today and rolling windows use UTC calendar boundaries', () => {
  assert.equal(filterItems([base],{...filters,period:'1'},[],'2026-09-23T08:00:00Z').length,0);
  assert.equal(filterItems([base],{...filters,period:'1'},[],'2026-09-22T23:59:59Z').length,1);
});
test('saved and confirmed code filters do not invent links', () => {
  assert.equal(filterItems([base],{...filters,savedOnly:true},['paper'],'2026-09-23').length,1);
  assert.equal(filterItems([base],{...filters,code:true},[],'2026-09-23').length,0);
  assert.equal(filterItems([{...base,code_url:'https://github.com/a/b'}],{...filters,code:true},[],'2026-09-23').length,1);
});
test('archives show old records', () => {
  const old={...base,published:'2020-01-01'};
  assert.equal(filterItems([old],filters,[],'2026-09-23').length,0);
  assert.equal(filterItems([old],{...filters,period:'all'},[],'2026-09-23').length,1);
});

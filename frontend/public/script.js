/* ================= helpers ================= */
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
/* ================= simulated time & date helpers ================= */
let timeOffset = Number(sessionStorage.getItem("sim_time_offset") || 0);
function getSimDate(){
  const d = new Date();
  d.setDate(d.getDate() + timeOffset);
  return d;
}
const pad2=n=>String(n).padStart(2,"0");
const iso=d=>{const x=new Date(d);return x.getFullYear()+"-"+pad2(x.getMonth()+1)+"-"+pad2(x.getDate())};
const daysAgo=n=>{const d=getSimDate();d.setDate(d.getDate()-n);return iso(d)};
const today=()=>iso(getSimDate());
const fmt=s=>new Date(s+"T12:00").toLocaleDateString(undefined,{month:"short",day:"numeric"});
const fmtD=d=>d.toLocaleDateString(undefined,{month:"short",day:"numeric"});
const LIMIT=3000;
function toast(m){const t=$("#toast");t.textContent=m;t.classList.add("on");clearTimeout(toast._t);toast._t=setTimeout(()=>t.classList.remove("on"),2200)}
const IC={
 home:'<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
 lib:'<path d="M4 4h5v16H4zM11 4h5v16h-5zM18 6l3 .8-3.6 13.4-3-.8z"/>',
 search:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
 spark:'<path d="M12 3l1.800 5.200L19 10l-5.200 1.800L12 17l-1.800-5.200L5 10l5.200-1.800z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
 chat:'<path d="M4 5h16v11H9l-5 4z"/>',plus:'<path d="M12 5v14M5 12h14"/>',check:'<path d="M5 12l5 5 9-10"/>',
 trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',edit:'<path d="M4 20h4L19 9l-4-4L4 16z"/>',x:'<path d="M6 6l12 12M18 6L6 18"/>',
 send:'<path d="M5 12h14M13 6l6 6-6 6"/>',lock:'<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
 back:'<path d="M19 12H5M11 6l-6 6 6 6"/>',expand:'<path d="M4 4h6M4 4v6M20 20h-6M20 20v-6M4 20l6-6M20 4l-6 6"/>'
};
const ic=n=>`<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${IC[n]}</svg>`;

/* ================= data layer (swap for backend calls) ================= */
const KEY="ai-book-assistant-v4";
function mkIsbn(n){const b="978"+String(100000000+n*7391531).slice(0,9);let s=0;for(let i=0;i<12;i++)s+=(+b[i])*(i%2?3:1);return b+((10-s%10)%10)} // sample ISBN-13s with a valid check digit
function B(id,title,author,pages,year,publisher,avg,genres,themes,desc,status="none",progress=0,rating=0,started=null,finished=null){return{isbn:mkIsbn(id),title,author,pages,year,publisher,avg,genres,themes,desc,status,progress,rating,started,finished}}
function seed(){
  const L=[32,41,28,40,36,30,45,22,38,34,40,29]; const log={}; L.forEach((p,i)=>log[daysAgo(i)]=p);
  const books=[
    B(1,"Circe","Madeline Miller",400,2018,"Little, Brown",4.3,["Fantasy","Mythology"],["isolation","identity","mythology"],"In the house of Helios, god of the sun, a daughter is born. Circe is a strange child, neither powerful nor viciously cruel like her father. Hungry for love, she turns to mortals and discovers that she has a gift for witchcraft that the gods fear. Banished to a deserted island, she hones her art, tames wild beasts and crosses paths with some of the most famous figures of myth.","progress",210,0,daysAgo(66)),
    B(2,"Project Hail Mary","Andy Weir",476,2021,"Ballantine",4.5,["Science fiction"],["isolation","friendship","science"],"Ryland Grace is the sole survivor on a desperate, last-chance mission, and if he fails, humanity and the Earth itself will perish. Except that right now, he doesn't know that. He can't even remember his own name, let alone the nature of his assignment.","progress",64,0,daysAgo(52)),
    B(3,"The Song of Achilles","Madeline Miller",378,2011,"Ecco",4.4,["Fantasy","Mythology"],["mythology","devotion","loss"],"Patroclus, an awkward young prince, has been exiled to the court of King Peleus and his perfect son Achilles. Despite their differences, the two form an unlikely friendship that deepens into something more as they grow into young men skilled in the arts of war and medicine.","finished",378,5,daysAgo(120),daysAgo(98)),
    B(4,"The Martian","Andy Weir",369,2014,"Crown",4.4,["Science fiction"],["survival","science","isolation"],"Six days ago, astronaut Mark Watney became one of the first people to walk on Mars. Now, he's sure he'll be the first person to die there, stranded after his crew believed him dead.","finished",369,4,daysAgo(90),daysAgo(80)),
    B(5,"The Night Circus","Erin Morgenstern",387,2011,"Doubleday",4.0,["Fantasy","Romance"],["magic","atmospheric"],"The circus arrives without warning. No announcements precede it. It is simply there, when yesterday it was not. Behind it, two young magicians are bound to a deadly competition.","unread"),
    B(6,"Piranesi","Susanna Clarke",272,2020,"Bloomsbury",4.2,["Fantasy","Mystery"],["solitude","mystery","isolation"],"Piranesi's house is no ordinary building: its rooms are infinite, its corridors endless, its walls lined with thousands upon thousands of statues. An ocean is trapped within, waiting to rise.","unread"),
    B(7,"Ariadne","Jennifer Saint",352,2021,"Celadon",4.1,["Fantasy","Mythology"],["mythology","betrayal"],"As princess of Crete, Ariadne grows up in the shadow of the labyrinth, where the Minotaur, her monstrous half-brother, is imprisoned. When Theseus arrives to slay the beast, she must decide how much to sacrifice for love."),
    B(8,"Rendezvous with Rama","Arthur C. Clarke",243,1973,"Gollancz",4.1,["Science fiction"],["exploration","mystery","science"],"At first, only a few things are known about the giant cylindrical object that has entered the solar system. Then a team of explorers boards it and finds a world with its own rules."),
    B(9,"Gone Girl","Gillian Flynn",422,2012,"Crown",4.1,["Mystery","Thriller"],["betrayal","identity","mystery"],"On a warm summer morning in North Carthage, Missouri, it is Nick and Amy Dunne's fifth wedding anniversary. Presents are being wrapped when Amy goes missing."),
    B(10,"The Thursday Murder Club","Richard Osman",382,2020,"Viking",4.1,["Mystery","Cozy"],["friendship","mystery"],"In a peaceful retirement village, four unlikely friends meet weekly to investigate cold cases. When a brutal killing takes place on their doorstep, they find themselves in the middle of their first live case."),
    B(11,"Dune","Frank Herbert",612,1965,"Chilton",4.3,["Science fiction"],["power","survival","betrayal"],"Set on the desert planet Arrakis, Dune is the story of the boy Paul Atreides, heir to a noble family tasked with ruling an inhospitable world where the only thing of value is the spice melange."),
    B(12,"Station Eleven","Emily St. John Mandel",333,2014,"Knopf",4.0,["Science fiction","Literary fiction"],["survival","art","identity"],"Years after a pandemic collapses civilization, a traveling troupe of actors and musicians moves between settlements, performing Shakespeare."),
    B(13,"Artemis","Andy Weir",305,2017,"Crown",3.7,["Science fiction","Thriller"],["survival","science","betrayal"],"Jazz Bashara is a criminal. Well, sort of. She lives in Artemis, the first and only city on the moon, and her smuggling side job is about to turn into something much bigger."),
    B(14,"The Hobbit","J.R.R. Tolkien",310,1937,"Allen & Unwin",4.3,["Fantasy","Adventure"],["friendship","exploration","magic"],"Bilbo Baggins is a hobbit who enjoys a quiet life, until the wizard Gandalf and a band of dwarves arrive to take him on an adventure to reclaim a lost treasure from the dragon Smaug."),
    B(15,"Murder on the Orient Express","Agatha Christie",256,1934,"Collins Crime Club",4.2,["Mystery","Classic"],["mystery","betrayal"],"Just after midnight, a snowdrift stops the Orient Express in its tracks. By morning, a passenger lies dead in his compartment. Hercule Poirot must find the killer among the travelers."),
    B(16,"And Then There Were None","Agatha Christie",272,1939,"Collins Crime Club",4.3,["Mystery","Classic"],["mystery","isolation","betrayal"],"Ten strangers are lured to an island off the Devon coast. As the night wears on, one by one, they begin to die.")
  ];
  const k=i=>books[i-1].isbn;
  return {name:"Reader",goal:40,yearGoal:12,favGenres:["Fantasy","Science fiction"],log,books,
    notes:{[k(1)]:[
      {id:"n1",type:"note",text:"Circe's loneliness on Aiaia feels like the heart of the book.",at:daysAgo(48)},
      {id:"n2",type:"highlight",text:"I decided that I would be the kind of witch who keeps her door open.",at:daysAgo(30)},
      {id:"n3",type:"note",text:"Love how Helios and the other gods are written as petty and cruel, not wise. The myths feel fresh.",at:daysAgo(12)}],
      [k(3)]:[{id:"n4",type:"note",text:"The last chapters are devastating. Rereading the opening after finishing changes everything.",at:daysAgo(98)}],
      [k(2)]:[{id:"n5",type:"note",text:"Rocky is already my favorite character. The friendship feels earned and the science is a joy.",at:daysAgo(20)}]},
    convs:[
      {id:"c1",title:"Short mysteries for a weekend",messages:[{role:"user",text:"Can you suggest a short mystery for a weekend?"},{role:"bot",text:"Here is one pick under 300 pages based on what you've read and rated:",picks:[{isbn:k(6),why:"272 pages, mystery, shares #isolation with Circe"}],used:["Your ratings","Your favorite genres"]}]},
      {id:"c2",title:"Themes in Circe",bookIsbn:k(1),messages:[{role:"user",text:"What are the themes of this book?"},{role:"bot",text:"Circe is built around #isolation, #identity and #mythology. Your own notes lean toward loneliness and how the gods are portrayed.",picks:[],used:["Book summary","Your notes on Circe"]}]}
    ]};
}
let S;try{S=JSON.parse(localStorage.getItem(KEY))}catch(e){S=null}
if(!S||!S.books)S=seed();
function save(){try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}  /* NFR-06: commit right away */
const book=isbn=>S.books.find(b=>b.isbn===String(isbn));
const inLib=b=>b.status!=="none";
const mine=()=>S.books.filter(inLib);
const notesOf=b=>S.notes[b.isbn]||[];

/* ================= derived values ================= */
const pct=b=>Math.min(100,Math.round(b.progress/b.pages*100));
const pagesToday=()=>S.log[today()]||0;
function streak(){let n=0,i=pagesToday()>0?0:1;while((S.log[daysAgo(i)]||0)>0){n++;i++}return n}
function avgPerDay(days=7){let t=0;for(let i=0;i<days;i++)t+=S.log[daysAgo(i)]||0;return Math.round(t/days)}
function suggestGoal(){const a=avgPerDay(7);return Math.max(10,Math.round(a*1.05/5)*5)}              /* FR-12 */
function estFinish(b){const n=S.books.filter(x=>x.status==="progress").length||1;const rate=Math.max(5,Math.round(avgPerDay(14)/n));const d=new Date();d.setDate(d.getDate()+Math.ceil((b.pages-b.progress)/rate));return {date:fmtD(d),rate}} /* FR-11 */
function goalAlert(){const left=S.goal-pagesToday();if(left<=0)return{t:"good",m:`You hit today's goal of ${S.goal} pages. Nice work.`};if(new Date().getHours()>=18)return{t:"warn",m:`You're ${left} page${left===1?"":"s"} behind today's goal. A short session tonight gets you there.`};return null} /* FR-15 */
function avgRating(){const f=S.books.filter(b=>b.status==="finished"&&b.rating);return f.length?(f.reduce((a,b)=>a+b.rating,0)/f.length).toFixed(1):"-"}
const finishedCount=()=>S.books.filter(b=>b.status==="finished").length;

/* mock local NLP: replace with the backend's theme / entity / sentiment output (FR-18..20) */
const THEME_WORDS={isolation:["alone","lonely","loneliness","isolated","solitude","island"],mythology:["god","gods","myth","myths","greek"],identity:["identity","herself","himself","who she","who he"],friendship:["friend","friendship","ally"],survival:["survive","survival","stranded"],science:["science","experiment","physics","engineer"],betrayal:["betray","betrayal","lied","trust"],devotion:["love","devotion","loyal"],mystery:["mystery","clue","secret","puzzle"],magic:["magic","witch","spell"],loss:["loss","grief","death","devastating"],power:["power","rule","king"]};
const POS=["love","favorite","joy","fresh","earned","beautiful","great","amazing","brilliant","fun"],NEG=["devastating","sad","boring","slow","hate","confusing","cruel","petty","dull"];
function analyze(list){const text=list.map(n=>n.text).join(" ");const low=text.toLowerCase();
  const themes=Object.entries(THEME_WORDS).map(([t,w])=>[t,w.reduce((a,x)=>a+(low.split(x).length-1),0)]).filter(x=>x[1]).sort((a,b)=>b[1]-a[1]).map(x=>x[0]).slice(0,4);
  const stop=new Set(["The","This","That","It","I","A","In","My","After","Love","Rereading","Rocky","Is"]);
  const ents=[...new Set((text.match(/\b[A-Z][a-z]{2,}\b/g)||[]).filter(w=>!stop.has(w)))].slice(0,5);
  const p=POS.reduce((a,x)=>a+(low.split(x).length-1),0),n=NEG.reduce((a,x)=>a+(low.split(x).length-1),0);
  const tone=p>n+1?"pos":n>p+1?"neg":(p||n)?"mix":"neu";return{themes,ents,tone}}

/* recommendations: Dashboard strategy stand-in (FR-23, FR-25). The real RecommendationEngine plugs in here. */
function recommend(o={}){
  const src=S.books.filter(b=>(b.status==="finished"&&b.rating>=4)||b.status==="progress");
  const noteThemes=new Set(src.flatMap(b=>analyze(notesOf(b)).themes));
  let pool=S.books.filter(b=>b.status==="none"||b.status==="unread");
  if(o.genre)pool=pool.filter(b=>b.genres.includes(o.genre));
  if(o.maxPages)pool=pool.filter(b=>b.pages<o.maxPages);
  if(o.theme)pool=pool.filter(b=>b.themes.includes(o.theme));
  return pool.map(b=>{
    let best=null;src.forEach(s=>{const th=b.themes.filter(t=>s.themes.includes(t));const g=b.genres.filter(x=>s.genres.includes(x));const sc=th.length*2+g.length+(s.author===b.author?3:0);if(!best||sc>best.sc)best={s,sc,th}});
    const fav=b.genres.find(g=>S.favGenres.includes(g)),nt=b.themes.filter(t=>noteThemes.has(t));
    const score=(best?best.sc:0)+(fav?2:0)+nt.length;
    const why=best&&best.s.author===b.author?`Same author as ${best.s.title}${best.s.rating?` (you rated it ${best.s.rating} stars)`:""}`
      :best&&best.th.length?`Shares ${best.th.map(t=>"#"+t).join(" and ")} with ${best.s.title}`
      :fav?`In your favorite genre: ${fav}`:"Popular with readers of your genres";
    return{isbn:b.isbn,b,match:Math.max(58,Math.min(97,52+score*6)),why}}).sort((a,c)=>c.match-a.match);
}
const byAuthor=b=>S.books.filter(x=>x.author===b.author&&x.isbn!==b.isbn);                     /* FR-04 */
function similar(b){return S.books.filter(x=>x.isbn!==b.isbn&&x.author!==b.author).map(x=>({b:x,sc:x.themes.filter(t=>b.themes.includes(t)).length*2+x.genres.filter(g=>b.genres.includes(g)).length})).filter(x=>x.sc>0).sort((a,c)=>c.sc-a.sc).slice(0,6).map(x=>x.b)} /* FR-05 */

/* state changes (book lifecycle: Unread > In progress > Finished, FR-06..10) */
function addToLibrary(b){b.status="unread";b.progress=0;save()}
function removeFromLibrary(b){b.status="none";b.progress=0;b.started=null;b.finished=null;save()}
function setProgress(b,n){n=Math.max(0,Math.min(b.pages,Math.round(n)||0));const add=n-b.progress;if(add>0)S.log[today()]=pagesToday()+add;b.progress=n;
  if(n>=b.pages){b.status="finished";b.finished=today();b.started=b.started||today()}
  else if(n>0){b.status="progress";b.started=b.started||today();b.finished=null}else{b.status="unread";b.started=null;b.finished=null}save();return add}
function reread(b){b.status="progress";b.progress=0;b.finished=null;b.started=today();save()}

/* ================= streak visuals ================= */
const FLAME='<svg viewBox="0 0 24 28" aria-hidden="true"><path d="M12 2c1 5 7 7 7 14a7 7 0 0 1-14 0c0-3.500 2-5 3.500-8 .8 2.200 2 2.500 3.500-6z"/></svg>';
function pumpkin(pct){
  const body='<ellipse cx="50" cy="54" rx="21" ry="30"/><ellipse cx="34" cy="54" rx="19" ry="28"/><ellipse cx="66" cy="54" rx="19" ry="28"/><ellipse cx="22" cy="56" rx="13" ry="23"/><ellipse cx="78" cy="56" rx="13" ry="23"/>';
  const y=Math.round(86-Math.min(100,pct)/100*62);
  return `<svg class="pumpkin" viewBox="0 0 100 96" role="img" aria-label="${pct}% of today\'s goal"><defs><clipPath id="pk-streak"><rect x="0" y="${y}" width="100" height="100"/></clipPath></defs>
  <g fill="rgba(255,240,230,0.12)" stroke="none">${body}</g>
  <g fill="#f27a1a" stroke="none" clip-path="url(#pk-streak)">${body}</g>
  <g fill="none" stroke="#8d5bc7" stroke-width="2.6">${body}</g>
  <path d="M47 27c0-9 3-14 9-16l3 5c-4 1-5 5-5 11z" fill="#5ba534" stroke="#8d5bc7" stroke-width="2" stroke-linejoin="round"/>
  <path d="M35 49l6 9H29z" fill="#2c1543" stroke="#8d5bc7" stroke-width="1.6" stroke-linejoin="round"/><path d="M65 49l6 9H59z" fill="#2c1543" stroke="#8d5bc7" stroke-width="1.6" stroke-linejoin="round"/>
  <path d="M36 68q14 11 28 0" fill="none" stroke="#8d5bc7" stroke-width="3.5" stroke-linecap="round"/></svg>`;
}

/* ================= visual pieces ================= */
const COVERS=[["#1e3a5f","#fff"],["#c2410c","#fff"],["#2f5d46","#fff"],["#6b2e5f","#fff"],["#d19a1f","#27211c"],["#1f6f78","#fff"],["#2d2a32","#f3d9a4"],["#9b2c2c","#fff"]];
function hash(t){let h=0;for(const c of t)h=(h*31+c.charCodeAt(0))>>>0;return h}
const cover=(b,cls="")=>{const[c,t]=COVERS[hash(b.title)%8];const img=/^https?:\/\//.test(b.cover||"")&&!/nophoto/.test(b.cover)?`<img src="${esc(b.cover)}" alt="" loading="lazy" referrerpolicy="no-referrer" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:inherit" onerror="this.parentNode.querySelector('.cv-label').hidden=false;this.remove()">`:"";const label=`<span class="cv-label"${img?" hidden":""}>${esc(b.title)}</span>`;return `<div class="cover ${cls}" style="--c:${c};--t:${t};position:relative" aria-hidden="true">${label}${img}</div>`};
const genreChips=b=>`<div class="chips">${b.genres.map(g=>`<a class="chip" href="#/browse?genre=${encodeURIComponent(g)}">${esc(g)}</a>`).join("")}</div>`;
const themeTags=(l,n=3)=>`<div class="chips">${l.slice(0,n).map(t=>`<span class="tag t${hash(t)%3}">#${esc(t)}</span>`).join("")}</div>`;
function pill(b){if(b.status==="unread")return`<span class="pill unread">Unread</span>`;if(b.status==="progress")return`<span class="pill progress">In progress${b.rating?" · rated":""}</span>`;if(b.status==="finished")return`<span class="pill finished">${ic("check")}${b.rating?"Finished · rated":"Finished"}</span>`;return""}
const starsStatic=(n,sm)=>`<span class="stars ${sm?"sm":""}" role="img" aria-label="${n} of 5 stars">${[1,2,3,4,5].map(i=>`<span class="${i<=n?"on":""}">&#9733;</span>`).join("")}</span>`;
const starInput=(b,sm=false)=>`<div class="stars ${sm?"sm":""}" role="group" aria-label="Your rating for ${esc(b.title)}">${[1,2,3,4,5].map(i=>`<button type="button" class="${i<=b.rating?"on":""}" data-act="rate" data-isbn="${b.isbn}" data-n="${i}" aria-label="${i} star${i>1?"s":""}" aria-pressed="${i===b.rating}">&#9733;</button>`).join("")}</div>`;
const counter=(id)=>`<div class="counter" id="${id}" aria-live="polite">0 / ${LIMIT}</div>`;
const arrowBack=`<a class="lnk" href="javascript:history.back()">${ic("back")} Back</a>`;

function recCard(r,{add=true}={}){const b=r.b||book(r.isbn);return `<article class="card rec"><a href="#/book/${b.isbn}" aria-label="${esc(b.title)}">${cover(b)}</a>
  <div><h3><a href="#/book/${b.isbn}" style="text-decoration:none">${esc(b.title)}</a></h3><p class="muted">${esc(b.author)}</p></div>
  <p class="match">${r.match}% match</p>${themeTags(b.themes,3)}<p class="why">${esc(r.why)}</p>
  <div class="act">${inLib(b)?pill(b):add?`<button class="btn sm" data-act="add" data-isbn="${b.isbn}">${ic("plus")} Add to library</button>`:""}</div></article>`}
const mini=b=>`<a class="mini" href="#/book/${b.isbn}">${cover(b)}<b>${esc(b.title)}</b><span class="muted">${esc(b.author)}</span>${themeTags(b.themes,2)}</a>`;

/* ================= backend API client (UserHandler facade, Sprint 3) ================= */
const API_BASE = (window.location && window.location.origin && window.location.origin.startsWith("http"))
  ? window.location.origin
  : "http://127.0.0.1:8000";

const api = {
  isBackendAvailable: false,

  async checkBackend(){
    try {
      const res = await fetch(`${API_BASE}/api/settings`, { method: "GET", signal: AbortSignal.timeout(1000) });
      if (res.ok) this.isBackendAvailable = true;
    } catch (e) {
      this.isBackendAvailable = false;
    }
    return this.isBackendAvailable;
  },

  async searchBooks(q="", genre=""){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(q)}&genre=${encodeURIComponent(genre)}`);
        if(res.ok) return await res.json();
      } catch(e) { console.warn("API search fallback:", e); }
    }
    const n = q.trim().toLowerCase();
    let l = S.books.filter(b=>(!n||[b.title,b.author,b.isbn,...b.genres].join(" ").toLowerCase().includes(n))&&(!genre||b.genres.includes(genre)));
    const top = l[0];
    const more = top ? byAuthor(top) : [];
    return { results: l, more_by_author: more };
  },

  async getBook(isbn){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/books/${isbn}`);
        if(res.ok) return await res.json();
      } catch(e) { console.warn("API getBook fallback:", e); }
    }
    const b = book(isbn);
    if(!b) return null;
    return {
      ...b,
      notes: notesOf(b),
      more_by_author: byAuthor(b),
      similar: similar(b)
    };
  },

  async saveProgress(isbn, pages){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/progress`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ isbn, pages: Number(pages), day: today() })
        });
        if(res.ok) {
          const b = book(isbn);
          if(b) setProgress(b, pages);
          return await res.json();
        }
      } catch(e){}
    }
    const b = book(isbn);
    if(b) setProgress(b, pages);
    return { ok: true };
  },

  async rateBook(isbn, rating){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/books/${isbn}/rate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating: Number(rating) })
        });
        if(res.ok) {
          const b = book(isbn);
          if(b){
            b.rating = rating;
            if(b.rating && b.status === "none"){
              b.status = "finished"; b.progress = b.pages; b.finished = today();
            }
            save();
          }
          return await res.json();
        }
      } catch(e){}
    }
    const b = book(isbn);
    if(b){
      b.rating = rating;
      if(b.rating && b.status === "none"){
        b.status = "finished"; b.progress = b.pages; b.finished = today();
      }
      save();
    }
    return { ok: true };
  },

  async addLibrary(isbn){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/library/add`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ isbn })
        });
        if(res.ok) {
          const b = book(isbn);
          if(b) addToLibrary(b);
          return await res.json();
        }
      } catch(e){}
    }
    const b = book(isbn);
    if(b) addToLibrary(b);
    return { ok: true };
  },

  async removeLibrary(isbn){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/library/${isbn}`, { method: "DELETE" });
        if(res.ok) {
          const b = book(isbn);
          if(b) removeFromLibrary(b);
          return await res.json();
        }
      } catch(e){}
    }
    const b = book(isbn);
    if(b) removeFromLibrary(b);
    return { ok: true };
  },

  async addNote(isbn, text, kind="note"){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ isbn, body: text, kind })
        });
        if(res.ok) {
          const data = await res.json();
          (S.notes[isbn] = S.notes[isbn] || []).push({
            id: String(data.note.id),
            type: kind,
            text,
            at: today()
          });
          save();
          return data;
        }
      } catch(e){}
    }
    const n = { id: "n" + Date.now(), type: kind, text, at: today() };
    (S.notes[isbn] = S.notes[isbn] || []).push(n);
    save();
    return { ok: true, note: n };
  },

  async editNote(noteId, text){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/notes/${noteId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: text })
        });
        if(res.ok) return await res.json();
      } catch(e){}
    }
    for(const k in S.notes){
      const found = S.notes[k].find(x => String(x.id) === String(noteId));
      if(found){ found.text = text; save(); break; }
    }
    return { ok: true };
  },

  async deleteNote(noteId, isbn){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/notes/${noteId}`, { method: "DELETE" });
        if(res.ok) {
          if(isbn && S.notes[isbn]){
            S.notes[isbn] = S.notes[isbn].filter(n => String(n.id) !== String(noteId));
            save();
          }
          return await res.json();
        }
      } catch(e){}
    }
    if(isbn && S.notes[isbn]){
      S.notes[isbn] = S.notes[isbn].filter(n => String(n.id) !== String(noteId));
      save();
    }
    return { ok: true };
  },

  async getRecommendations(genre="", limit=4){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/dashboard?genre=${encodeURIComponent(genre)}&limit=${limit}`);
        if(res.ok) return await res.json();
      } catch(e){}
    }
    return recommend({ genre }).slice(0, limit);
  },

  async askAssistant(text, isbn=null){
    await this.checkBackend();
    if(this.isBackendAvailable){
      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text, isbn })
        });
        if(res.ok) return await res.json();
      } catch(e){}
    }
    return mockAsk(text, isbn);
  }
};

/* ================= views ================= */

function daysSinceLastRead(){
  if(pagesToday() > 0) return 0;
  for(let i = 1; i <= 60; i++){
    if((S.log[daysAgo(i)] || 0) > 0) return i;
  }
  return 99;
}

function getGreetingInfo(name){
  const d = getSimDate();
  const dayName = d.toLocaleDateString(undefined, { weekday: "long" });
  const hr = d.getHours();
  const st = streak();
  const goalMet = pagesToday() >= S.goal;
  const daysIdle = daysSinceLastRead();

  // Snarky/playful if user hasn't logged reading in a long time (>= 4 days)
  if(daysIdle >= 4){
    const snarky = [
      `Hello, will you even use this app today, ${name}? (¬_¬)`,
      `Look who decided to open the app! Welcome back, ${name} (・∀・)`,
      `Are the books too heavy to open today, ${name}? (・_・;)`,
      `Rumor has it your bookmarks are feeling lonely, ${name}... (っ˘ω˘ς)`
    ];
    const title = snarky[d.getDate() % snarky.length];
    return {
      title,
      sub: `It's been ${daysIdle} days since your last read. Even 5 pages will wake the pumpkin up! (ง •̀_•́)ง`
    };
  }

  // Lost streak recently (1 to 3 days idle)
  if(st === 0 && daysIdle >= 1){
    return {
      title: `Ready for a comeback, ${name}? (ง •̀_•́)ง`,
      sub: `The streak took a nap, but today is page one of a brand new chapter! (◕‿◕)`
    };
  }

  // Goal met today
  if(goalMet){
    return {
      title: `Goal crushed today, ${name}! (＾▽＾)`,
      sub: `You hit your ${S.goal} pages! Feel free to read more or bask in glory (★ω★).`
    };
  }

  // High streak
  if(st >= 3){
    return {
      title: `You're on fire, ${name}! (★ω★)`,
      sub: `${st}-day streak and counting! Keep that reading momentum going (ง •̀_•́)ง`
    };
  }

  // Daily varied greetings with kaomoji
  const dayGreetings = {
    "Monday": `Happy Monday, ${name}! (◕‿◕)`,
    "Tuesday": `Happy Tuesday, ${name}! (っ˘ω˘ς)`,
    "Wednesday": `Midweek reading time, ${name}! (＾▽＾)`,
    "Thursday": `Almost Friday, ${name}! Keep turning pages (ง •̀_•́)ง`,
    "Friday": `Happy Friday, ${name}! (☆▽☆)`,
    "Saturday": `Weekend reading mode activated, ${name}! (っ˘ω˘ς)`,
    "Sunday": `Cozy Sunday vibes, ${name}! (◕‿◕)`
  };

  const title = dayGreetings[dayName] || `Welcome back, ${name}! (◕‿◕)`;
  const sub = hr >= 21
    ? `Late-night reading session? Don't forget to sleep! (¬‿¬)`
    : hr < 11
    ? `Morning coffee and a good book? Best combination (っ˘ω˘ς).`
    : `Here is where you stand today.`;

  return { title, sub };
}

function viewHome(){
  const reading=S.books.filter(b=>b.status==="progress"),g=Math.min(100,Math.round(pagesToday()/S.goal*100)),left=Math.max(0,S.goal-pagesToday());
  const al=goalAlert(),sg=suggestGoal(),done=finishedCount(),recs=recommend().slice(0,4);
  const week=[...Array(7)].map((_,i)=>daysAgo(6-i));
  const greetingName=(S.name&&S.name.trim().toLowerCase()!=="reader")?esc(S.name.trim()):"reader";
  const greetingInfo=getGreetingInfo(greetingName);

  const st=streak();
  const daysIdle=daysSinceLastRead();
  let streakTitle="You're on a roll! (ง •̀_•́)ง";
  let streakLead="";
  if(st===0){
    if(daysIdle>=4){
      streakTitle="Oops! You lost your streak! (；・∀・)";
      streakLead=left?`The dust is thick, but <b>${left} more page${left===1?"":"s"}</b> will resurrect your streak! (ง •̀_•́)ง`:"Today's pumpkin is full and your new streak is underway! (＾▽＾)";
    }else{
      streakTitle="Oops! You lost your streak! (・_・;)";
      streakLead=left?`Don't let yesterday win — read <b>${left} more page${left===1?"":"s"}</b> today to start fresh! (◕‿◕)`:"Today's pumpkin is full and your new streak is underway! (＾▽＾)";
    }
  }else if(st>=2){
    streakTitle="You're on a roll! (ง •̀_•́)ง";
    streakLead=left?`<b>${left} more page${left===1?"":"s"}</b> needed to hit today's streak and fill today's pumpkin. (っ˘ω˘ς)`:`Today's pumpkin is overflowing! You've kept your <b>${st}-day streak</b> alive! (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧`;
  }else{
    if(pagesToday()===0){
      streakTitle="Don't lose your streak! (・_・;)";
      streakLead=`<b>${left} more page${left===1?"":"s"}</b> needed today to keep your streak alive! (ง •̀_•́)ง`;
    }else{
      streakTitle=left?"Streak in progress! (◕‿◕)":"You're on a roll! (＾▽＾)";
      streakLead=left?`<b>${left} more page${left===1?"":"s"}</b> and today's pumpkin is full! (っ˘ω˘ς)`:`Today's pumpkin is full! Day 1 streak secured (＾▽＾).`;
    }
  }

  main.innerHTML=`
  <div class="sim-bar" role="region" aria-label="Time simulation controls">
    <div><span class="badge">Time Machine</span> <b>${fmtD(getSimDate())}</b>${timeOffset!==0?` (${timeOffset>0?'+'+timeOffset:timeOffset} day${Math.abs(timeOffset)===1?'':'s'} simulated)`:' (Real Date)'} · Test your reading streaks & day changes:</div>
    <div class="acts">
      <button type="button" data-act="sim-skip" title="Advance 1 day with no reading to see a lost streak">+1 Day (Skip Reading)</button>
      <button type="button" data-act="sim-goal" title="Log daily goal and advance 1 day to see streak grow">+1 Day (Hit Goal)</button>
      ${timeOffset!==0?`<button type="button" data-act="sim-reset" title="Reset back to today">Reset to Today</button>`:''}
    </div>
  </div>
  <div class="head"><div><h1>${greetingInfo.title}</h1><p>${greetingInfo.sub}</p></div></div>
  ${al&&!viewHome.dismissed?`<div class="alert ${al.t}" role="status"><span>${esc(al.m)}</span><button data-act="dismiss" aria-label="Dismiss">${ic("x")}</button></div>`:""}
  <section class="card goals" aria-label="Reading goals">
    <div class="goal"><h2>Today's goal</h2>
      <div class="big">${pagesToday()} <small>of ${S.goal} pages</small></div>
      <div class="bar ${left?"":"good"}" role="progressbar" aria-valuenow="${g}" aria-valuemin="0" aria-valuemax="100" aria-label="Daily goal progress"><i style="width:${g}%"></i></div>
      <p class="sub">${left?`<b>${left} pages</b> to go`:"<b>Goal reached</b>"} · averaging ${avgPerDay()} pages a day this week</p>
      ${Math.abs(sg-S.goal)>=3?`<div class="suggest"><span>Suggested goal: <b>${sg} pages</b>, based on your last 7 days.</span><button class="btn sm" data-act="use-goal" data-n="${sg}">Use ${sg}</button></div>`:""}
      <details class="edit"><summary>Change daily goal</summary><form data-form="goal"><label class="sr" for="hg">Daily goal in pages</label><input class="in" id="hg" type="number" min="1" max="500" value="${S.goal}"><button class="btn sm">Save</button></form></details>
      <span class="streak">${streak()}-day reading streak</span></div>
    <div class="goal"><h2>${new Date().getFullYear()} reading challenge</h2>
      <div class="big">${done} <small>of ${S.yearGoal} books</small></div>
      <div class="bar" role="progressbar" aria-valuenow="${Math.round(done/S.yearGoal*100)}" aria-valuemin="0" aria-valuemax="100" aria-label="Yearly goal progress"><i style="width:${Math.min(100,done/S.yearGoal*100)}%"></i></div>
      <p class="sub">${done>=S.yearGoal?"<b>Goal reached</b>":`<b>${S.yearGoal-done} to go</b>`} · average rating ${avgRating()} of 5</p>
      <p class="sub"><a class="lnk" href="#/settings">Change goals in Settings</a></p></div>
  </section>

  <section class="sec" aria-labelledby="h-cont"><div class="sec-h"><h2 id="h-cont">Continue reading</h2><a class="lnk" href="#/library">Open My Library</a></div>
    ${reading.length?`<div class="cont">${reading.map(b=>{const e=estFinish(b);return `<article class="card rc"><a href="#/book/${b.isbn}" aria-label="${esc(b.title)}">${cover(b)}</a><div class="b">
      <h3><a href="#/book/${b.isbn}">${esc(b.title)}</a></h3><p class="muted">${esc(b.author)}${b.started?` · started ${fmt(b.started)}`:""}</p>
      <div class="bar" role="progressbar" aria-valuenow="${pct(b)}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct(b)}%"></i></div>
      <p class="muted">${b.progress} of ${b.pages} pages · est. finish ${e.date} (~${e.rate} pages/day)</p>
      <form class="logf" data-form="log" data-isbn="${b.isbn}"><label class="sr" for="lp${b.isbn}">Pages read today in ${esc(b.title)}</label><input class="in" id="lp${b.isbn}" type="number" min="1" max="${b.pages-b.progress}" placeholder="Pages"><button class="btn sm pri">Log pages</button><span class="muted small" style="margin-left:auto">${left?`${left} page${left===1?"":"s"} to streak`:`<span style="color:var(--good);font-weight:600">✓ Streak goal met</span>`}</span></form></div></article>`}).join("")}</div>`
      :`<div class="card empty">Nothing in progress. <a class="lnk" href="#/browse">Find a book to start</a>.</div>`}
  </section>

  <section class="sec" aria-labelledby="h-streak">
    <div class="sec-h"><div><h2 id="h-streak">Streak tracking</h2><p>Track how much is needed to hit today's streak</p></div></div>
    <div class="streak-hero card" aria-label="Streak tracking">
      <div>
        <h3>${streakTitle}</h3>
        <p class="lead">${streakLead}</p>
        <div class="candles" role="img" aria-label="Last 7 days: lit flame means you hit your goal">${week.map(d=>{const v=S.log[d]||0;return `<div class="candle ${v>=S.goal?"full":v>0?"some":"out"}" title="${fmt(d)}: ${v} pages read${v>=S.goal?' (goal met)':''}">${FLAME}<span>${new Date(d+"T12:00").toLocaleDateString(undefined,{weekday:"narrow"})}</span></div>`}).join("")}</div>
        <div class="streak-pills">
          <span><b>${streak()}</b> day streak</span>
          <span><b>${done}</b> of ${S.yearGoal} books</span>
          <span><b>${avgRating()}</b> avg rating</span>
        </div>
      </div>
      <div class="pumpkin-wrap">${pumpkin(g)}<div class="cap">${pagesToday()} <small>of ${S.goal} pages</small></div></div>
    </div>
  </section>

  <section class="sec" aria-labelledby="h-pick"><div class="sec-h"><div><h2 id="h-pick">Picked for you</h2><p>Based on your ratings, notes and favorite genres</p></div><a class="lnk" href="#/for-you">See all recommendations</a></div>
    <div class="gp"><span>Your genres:</span><div class="chips">${S.favGenres.map(g=>`<a class="chip" href="#/for-you?genre=${encodeURIComponent(g)}">${esc(g)}</a>`).join("")||'<a class="lnk" href="#/settings">Choose favorite genres</a>'}</div></div>
    ${recs.length?`<div class="recs">${recs.map(r=>recCard(r)).join("")}</div>`:`<div class="card empty">You've added every book in the catalog. Check back after adding more.</div>`}
  </section>`;
}

const lib={tab:"all",q:"",sort:"recent",open:new Set()};
function viewLibrary(p){
  lib.tab=p.get("tab")||lib.tab;const all=mine();
  const cnt=t=>t==="all"?all.length:all.filter(b=>b.status===t).length;
  let l=all.filter(b=>lib.tab==="all"||b.status===lib.tab).filter(b=>(b.title+" "+b.author+" "+b.isbn).toLowerCase().includes(lib.q.toLowerCase()));
  const k=lib.sort;l.sort((a,b)=>k==="rating"?b.rating-a.rating:k==="recent"?S.books.indexOf(b)-S.books.indexOf(a):String(a[k]).localeCompare(String(b[k])));
  main.innerHTML=`
  <div class="head"><div><h1>My Library</h1><p>The books you're tracking, with your notes right under each one.</p></div><a class="btn pri" href="#/browse">${ic("plus")} Add books</a></div>
  <div class="tabs" role="tablist" aria-label="Filter by status">${[["all","All"],["progress","In progress"],["unread","Unread"],["finished","Finished"]].map(([v,n])=>`<a role="tab" aria-selected="${lib.tab===v}" class="${lib.tab===v?"on":""}" href="#/library?tab=${v}">${n}<span class="n">${cnt(v)}</span></a>`).join("")}</div>
  <div class="bar-tools"><label class="sr" for="lq">Filter library</label><input class="in grow" id="lq" type="search" placeholder="Filter by title, author or ISBN" value="${esc(lib.q)}">
    <label class="sr" for="ls">Sort</label><select class="in" id="ls"><option value="recent">Sort: recently added</option><option value="title">Sort: title</option><option value="author">Sort: author</option><option value="rating">Sort: my rating</option></select></div>
  <div id="lbody"></div>`;
  $("#ls").value=lib.sort;
  const draw=()=>{
    $("#lbody").innerHTML=l.length?`<div class="card tw"><table class="t"><thead><tr><th></th><th>Book</th><th>Status</th><th class="h">Progress</th><th>My rating</th><th>Notes</th></tr></thead><tbody>${l.map(b=>{const open=lib.open.has(b.isbn),nn=notesOf(b).length;return `<tr class="${open?"exp":""}">
      <td style="width:68px"><a href="#/book/${b.isbn}" aria-label="${esc(b.title)}">${cover(b)}</a></td>
      <td><a class="ttl" href="#/book/${b.isbn}">${esc(b.title)}</a><br><span class="muted">${esc(b.author)} · ISBN <span class="isbn">${b.isbn}</span></span></td>
      <td>${pill(b)}</td>
      <td class="h" style="min-width:150px">${b.status==="progress"?`<div class="bar"><i style="width:${pct(b)}%"></i></div><span class="muted">${pct(b)}% · ${b.progress}/${b.pages} pages</span>`:b.status==="finished"?`<span class="muted">Finished ${b.finished?fmt(b.finished):""}</span>`:`<span class="muted">${b.pages} pages</span>`}</td>
      <td>${starInput(b)}</td>
      <td><button class="nb" data-act="notes" data-isbn="${b.isbn}" aria-expanded="${open}" aria-controls="nr-${b.isbn}">${nn} note${nn===1?"":"s"}</button></td></tr>
      ${open?`<tr class="notesrow" id="nr-${b.isbn}"><td colspan="6">${notesBlock(b,true)}</td></tr>`:""}`}).join("")}</tbody></table></div>`
      :`<div class="card empty">${all.length?"No books match this filter.":"Your library is empty."} <a class="lnk" href="#/browse">Browse books to add</a>.</div>`;
  };draw();
  $("#lq").addEventListener("input",e=>{lib.q=e.target.value;viewLibrary(p);const q=$("#lq");q.focus();q.setSelectionRange(q.value.length,q.value.length)});
  $("#ls").addEventListener("change",e=>{lib.sort=e.target.value;viewLibrary(p)});
}

const br={q:"",genre:"",sort:"title"};
async function viewBrowse(p){
  br.q=(p.get("q")||"").slice(0,200);br.genre=p.get("genre")||"";
  const genres=[...new Set(S.books.flatMap(b=>b.genres))].sort();
  main.innerHTML=`
  <div class="head"><div><h1>${br.q?"Search results":"Browse books"}</h1><p>${br.q?`Showing matches for "${esc(br.q)}".`:"Search by title or author, or look through every book in the catalog."}</p></div></div>
  <form class="bar-tools" id="bf" role="search"><label class="sr" for="bq">Search</label><input class="in grow" id="bq" type="search" maxlength="200" placeholder="Title or author" value="${esc(br.q)}">
    <label class="sr" for="bg">Genre</label><select class="in" id="bg"><option value="">All genres</option>${genres.map(g=>`<option ${br.genre===g?"selected":""}>${esc(g)}</option>`).join("")}</select>
    <label class="sr" for="bs">Sort</label><select class="in" id="bs"><option value="title">Sort: title</option><option value="author">Sort: author</option><option value="avg">Sort: average rating</option></select><button class="btn pri">Search</button></form>
  <div id="bres" aria-live="polite"><p class="muted">Loading books…</p></div>`;
  $("#bs").value=br.sort;

  const searchData = await api.searchBooks(br.q, br.genre);
  let l = searchData.results || [];
  l.sort((a,b)=>br.sort==="avg"?(b.avg||b.avg_rating)-(a.avg||a.avg_rating):String(a[br.sort]).localeCompare(String(b[br.sort])));
  let html=l.length?`<p class="muted" style="margin-bottom:10px">${l.length} book${l.length===1?"":"s"}</p><div class="rl">${l.map(b=>`<article class="card res">${`<a href="#/book/${b.isbn}" aria-label="${esc(b.title)}">${cover(b)}</a>`}
    <div class="b"><h3><a href="#/book/${b.isbn}">${esc(b.title)}</a></h3><p class="muted">by <a class="lnk" href="#/browse?q=${encodeURIComponent(b.author)}">${esc(b.author)}</a> · ${b.pages} pages · ${(Number(b.avg||b.avg_rating||4.0)).toFixed(1)} avg rating · ISBN <span class="isbn">${b.isbn}</span></p>
    <p class="d">${esc(b.desc||b.summary)}</p><div class="chips" style="gap:10px">${genreChips(b).replace('class="chips"','class="chips"')}${themeTags(b.themes,3)}</div></div>
    <div class="side">${inLib(b)?pill(b):`<button class="btn sm" data-act="add" data-isbn="${b.isbn}">${ic("plus")} Add to library</button>`}<a class="btn sm" href="#/book/${b.isbn}">View</a></div></article>`).join("")}</div>`
    :`<div class="card empty"><b>No books match "${esc(br.q)}".</b><br>Try a shorter title, or search by the author's name.</div>`;
  if(l.length&&(br.q||br.genre)){
    const top=l[0];
    const more = (searchData.more_by_author && searchData.more_by_author.length) ? searchData.more_by_author.filter(x=>x.isbn!==top.isbn) : byAuthor(top);
    const sim=similar(top);
    html+=`<section class="sec" aria-labelledby="h-more"><div class="sec-h"><h2 id="h-more">More by ${esc(top.author)}</h2></div>${more.length?`<div class="minis">${more.map(mini).join("")}</div>`:`<div class="card empty">No other books by ${esc(top.author)} in the catalog yet.</div>`}</section>
    <section class="sec" aria-labelledby="h-sim"><div class="sec-h"><div><h2 id="h-sim">Similar books</h2><p>Matching the themes of ${esc(top.title)}</p></div></div>${sim.length?`<div class="minis">${sim.map(mini).join("")}</div>`:`<div class="card empty">No similar books found.</div>`}</section>`;
  }
  $("#bres").innerHTML=html;
  $("#bf").addEventListener("submit",e=>{e.preventDefault();goBrowse($("#bq").value,$("#bg").value)});
  $("#bg").addEventListener("change",()=>goBrowse($("#bq").value,$("#bg").value));
  $("#bs").addEventListener("change",e=>{br.sort=e.target.value;viewBrowse(p)});
}
function goBrowse(q,g){q=q.trim().slice(0,200);const a=[];if(q)a.push("q="+encodeURIComponent(q));if(g)a.push("genre="+encodeURIComponent(g));location.hash="#/browse"+(a.length?"?"+a.join("&"):"")}

function viewForYou(p){
  const g=p.get("genre")||"",all=recommend();
  const gs=[...S.favGenres,...[...new Set(all.flatMap(r=>r.b.genres))].filter(x=>!S.favGenres.includes(x)).sort()];
  const l=g?all.filter(r=>r.b.genres.includes(g)):all;
  main.innerHTML=`
  <div class="head"><div><h1>For You</h1><p>Books you haven't read, ranked by your ratings, notes and favorite genres.</p></div><a class="btn" href="#/assistant">${ic("chat")} Ask the assistant instead</a></div>
  <div class="tabs" role="tablist" aria-label="Filter by genre"><a role="tab" aria-selected="${!g}" class="${!g?"on":""}" href="#/for-you">All genres</a>${gs.map(x=>`<a role="tab" aria-selected="${g===x}" class="${g===x?"on":""}" href="#/for-you?genre=${encodeURIComponent(x)}">${esc(x)}</a>`).join("")}</div>
  ${l.length?`<div class="recs">${l.map(r=>recCard(r)).join("")}</div>`:`<div class="card empty">No unread ${g?esc(g)+" ":""}books left to recommend. Try another genre.</div>`}`;
}

function notesBlock(b,compact){
  const ns=notesOf(b),editing=viewBook.editing;
  const item=n=>editing===n.id?`<form class="note" data-form="note-save" data-isbn="${b.isbn}" data-id="${n.id}"><label class="l" for="ne${n.id}">Edit ${n.type}</label><textarea class="in" id="ne${n.id}" data-limit="${LIMIT}" data-ct="nec${n.id}">${esc(n.text)}</textarea>${counter("nec"+n.id)}<div class="acts"><button class="btn sm pri">Save</button><button type="button" class="btn sm" data-act="note-cancel">Cancel</button></div></form>`
   :`<div class="note ${n.type==="highlight"?"hl":""}"><div class="meta"><span>${n.type==="highlight"?"Highlight":"Note"} · ${fmt(n.at)}</span></div><div class="nt">${esc(n.text)}</div><div class="acts"><button class="btn sm" data-act="note-edit" data-isbn="${b.isbn}" data-id="${n.id}">${ic("edit")} Edit</button><button class="btn sm warn" data-act="note-del" data-isbn="${b.isbn}" data-id="${n.id}">${ic("trash")} Delete</button></div></div>`;
  const fid="nf"+b.isbn+(compact?"c":"");
  return `<div class="notes">${ns.length?ns.map(item).join(""):`<p class="muted">No notes yet. Add the first one below. Notes help the assistant and your recommendations.</p>`}</div>
  <form data-form="note-add" data-isbn="${b.isbn}"><label class="l" for="${fid}">Add to notes</label>
   <div class="row" style="margin-bottom:8px"><label class="l" style="margin:0" for="${fid}t">Type</label><select class="in" id="${fid}t" style="width:auto" name="type"><option value="note">Note</option><option value="highlight">Highlight</option></select></div>
   <textarea class="in" id="${fid}" data-limit="${LIMIT}" data-ct="${fid}c" placeholder="A thought, a question, or a line you want to keep"></textarea>${counter(fid+"c")}
   <div style="margin-top:8px"><button class="btn pri sm">Save note</button></div></form>`;
}
async function viewBook(isbn){
  main.innerHTML = `<div class="card empty">Loading book details…</div>`;
  const b = await api.getBook(isbn);
  if(!b){main.innerHTML=`<div class="card empty">That book isn't in the catalog. <a class="lnk" href="#/browse">Back to Browse</a></div>`;return}
  const more = (b.more_by_author && b.more_by_author.length) ? b.more_by_author : byAuthor(b);
  const sim = (b.similar && b.similar.length) ? b.similar : similar(b);
  const ns = (b.notes && b.notes.length) ? b.notes : notesOf(b);
  const a = ns.length ? analyze(ns) : null;
  const e = b.status === "progress" ? estFinish(b) : null;
  main.innerHTML=`
  <p style="margin-bottom:14px">${arrowBack}</p>
  <section class="card bk">${cover(b)}<div>
    <div class="row" style="gap:12px"><h1>${esc(b.title)}</h1>${pill(b)}</div>
    <p class="by">by <a href="#/browse?q=${encodeURIComponent(b.author)}">${esc(b.author)}</a></p>
    <dl class="facts">
      <div><dt>ISBN-13 (book ID)</dt><dd class="isbn">${b.isbn}</dd></div>
      <div><dt>Pages</dt><dd>${b.pages}</dd></div>
      <div><dt>Published</dt><dd>${esc(b.publisher)}, ${b.year}</dd></div>
      <div><dt>Average rating</dt><dd>${starsStatic(Math.round(b.avg||b.avg_rating||4.0),true)} <span class="muted small">${(Number(b.avg||b.avg_rating||4.0)).toFixed(1)}</span></dd></div>
      <div><dt>Your rating</dt><dd class="row" style="gap:6px;align-items:center">${starInput(b,true)} <span class="muted small">${b.rating?`<b>${b.rating}</b>/5`:'<span style="color:var(--orange);font-weight:600">Rate</span>'}</span></dd></div>
    </dl>
    <div class="chips" style="gap:10px;margin-bottom:12px">${genreChips(b)}${themeTags(b.themes,4)}</div>
    <p class="dsc cl" id="dsc">${esc(b.desc||b.summary)}</p><button class="lnk" data-act="more" aria-expanded="false" style="margin-top:4px">Show all</button>
    <div class="row" style="margin-top:16px">${inLib(b)?`<button class="btn" data-act="remove" data-isbn="${b.isbn}">Remove from library</button>`:`<button class="btn pri" data-act="add" data-isbn="${b.isbn}">${ic("plus")} Add to library</button>`}
      <button class="btn" data-act="askbook" data-isbn="${b.isbn}">${ic("chat")} Ask the assistant about this book</button></div>
  </div></section>

  <div class="two">
    <section class="card pn" aria-labelledby="h-me"><h2 id="h-me">Your reading</h2>
      ${!inLib(b)?`
      <p class="muted" style="margin-bottom:10px">Not yet in your library. Add it to log pages, or rate it right now.</p>
      <div class="row" style="margin-bottom:16px"><button class="btn sm pri" data-act="add" data-isbn="${b.isbn}">${ic("plus")} Add to library</button></div>
      <div><span class="l" id="rl">Your rating</span><div class="row" style="gap:8px;align-items:center">${starInput(b)} <span class="muted">${b.rating?`<b>${b.rating}</b> of 5 stars`:"Click a star to rate"}</span></div></div>
      `:`
      ${b.status==="finished"&&!b.rating?`<div class="prompt">You finished this book. How would you rate it?</div>`:""}
      <div class="row" style="margin-bottom:12px">${pill(b)}${b.started?`<span class="muted">Started ${fmt(b.started)}${b.finished?` · finished ${fmt(b.finished)}`:""}</span>`:'<span class="muted">Not started</span>'}</div>
      <form data-form="pages" data-isbn="${b.isbn}"><label class="l" for="pg">Pages read (of ${b.pages})</label><div class="row"><input class="in" id="pg" type="number" min="0" max="${b.pages}" value="${b.progress}" style="width:120px"><button class="btn sm pri">Update pages</button>${b.status==="finished"?`<button type="button" class="btn sm" data-act="reread" data-isbn="${b.isbn}">Read again</button>`:""}</div></form>
      <div class="bar ${b.status==="finished"?"good":""}" style="margin-top:12px"><i style="width:${pct(b)}%"></i></div>
      ${e?`<p class="est">Estimated finish <b>${e.date}</b>, at about ${e.rate} pages a day.</p>`:""}
      <div style="margin-top:16px"><span class="l" id="rl">Your rating</span><div class="row" style="gap:8px;align-items:center">${starInput(b)} <span class="muted">${b.rating?`<b>${b.rating}</b> of 5 stars`:"Click a star to rate"}</span></div></div>`}
    </section>
    <section class="card pn" aria-labelledby="h-ins"><h2 id="h-ins">Insights from your notes</h2>
      ${a?`<div class="ins"><div><div class="lbl">THEMES</div>${a.themes.length?themeTags(a.themes,4):'<span class="muted">No clear themes yet</span>'}</div>
        <div><div class="lbl">PEOPLE AND PLACES MENTIONED</div>${a.ents.length?`<div class="chips">${a.ents.map(x=>`<span class="chip">${esc(x)}</span>`).join("")}</div>`:'<span class="muted">None found</span>'}</div>
        <div><div class="lbl">OVERALL TONE</div><div class="tone ${a.tone==="neg"?"neg":a.tone==="mix"?"mix":""}" aria-label="${{pos:"Mostly positive",neg:"Mostly negative",mix:"Mixed",neu:"Neutral"}[a.tone]}">${[1,2,3,4,5].map(i=>`<i class="${({pos:5,neg:2,mix:3,neu:3}[a.tone])>=i?"on":""}"></i>`).join("")}<span class="muted" style="margin-left:8px">${{pos:"Mostly positive",neg:"Mostly negative",mix:"Mixed",neu:"Neutral"}[a.tone]}</span></div></div>
        <p class="muted">Worked out on this computer from your ${ns.length} note${ns.length===1?"":"s"}.</p></div>`
        :`<p class="muted">Write a note and this card will show the themes, names and tone found in it.</p>`}
    </section>
  </div>

  <section class="card pn" style="margin-top:18px" aria-labelledby="h-nt"><h2 id="h-nt">Notes</h2>${notesBlock(b,false)}</section>

  <section class="sec" aria-labelledby="h-ma"><div class="sec-h"><h2 id="h-ma">More by ${esc(b.author)}</h2></div>${more.length?`<div class="minis">${more.map(mini).join("")}</div>`:`<div class="card empty">No other books by ${esc(b.author)} in the catalog yet.</div>`}</section>
  <section class="sec" aria-labelledby="h-sb"><div class="sec-h"><div><h2 id="h-sb">Similar books</h2><p>Sharing themes with ${esc(b.title)}</p></div></div>${sim.length?`<div class="minis">${sim.map(mini).join("")}</div>`:`<div class="card empty">No similar books found.</div>`}</section>`;
}
function viewAssistant(p){
  const cid=p.get("c"),bk=p.get("book")?book(p.get("book")):null,conv=cid?S.convs.find(c=>c.id===cid):null;
  main.innerHTML=`<div class="head"><div><h1>Assistant</h1><p>Ask about your books and notes. Ask for suggestions whenever you want some.</p></div></div>
  <div class="ap"><aside class="card past" aria-label="Past conversations"><a class="btn pri sm" href="#/assistant" style="width:100%">${ic("plus")} New conversation</a><h2>Past conversations</h2>
    ${S.convs.length?S.convs.map(c=>`<a class="c ${conv&&conv.id===c.id?"on":""}" href="#/assistant?c=${c.id}">${esc(c.title)}</a>`).join(""):`<p class="muted" style="padding:6px 4px">Nothing yet. Your conversations are saved here.</p>`}</aside>
    <div id="cm"></div></div>`;
  mountChat($("#cm"),{convId:conv?conv.id:null,bookIsbn:bk?bk.isbn:(conv&&conv.bookIsbn)||null});
}

function viewSettings(){
  const genres=[...new Set(S.books.flatMap(b=>b.genres))].sort(),sg=suggestGoal();
  main.innerHTML=`<div class="head"><div><h1>Settings</h1><p>Everything here is saved on this computer. There is no account or sign-in.</p></div></div>
  <div class="st">
   <section class="card pn" aria-labelledby="s1"><h2 id="s1">Profile</h2><p>Used for the greeting on Home.</p>
     <form data-form="profile"><label class="l" for="nm">Display name</label><div class="row"><input class="in grow" id="nm" maxlength="40" value="${esc(S.name)}"><button class="btn pri sm">Save</button></div></form></section>
   <section class="card pn" aria-labelledby="s2"><h2 id="s2">Reading goals</h2><p>Your daily goal drives the progress bar and alerts on Home.</p>
     <form data-form="goals"><div class="row" style="align-items:flex-end"><div><label class="l" for="sg">Pages per day</label><input class="in" id="sg" type="number" min="1" max="500" value="${S.goal}" style="width:120px"></div>
       <div><label class="l" for="sy">Books this year</label><input class="in" id="sy" type="number" min="1" max="200" value="${S.yearGoal}" style="width:120px"></div><button class="btn pri sm">Save goals</button></div></form>
     <p class="muted" style="margin-top:12px">Suggested from your last 7 days: <b>${sg} pages a day</b>. <button class="lnk" data-act="use-goal" data-n="${sg}">Use suggestion</button></p></section>
   <section class="card pn" aria-labelledby="s3"><h2 id="s3">Favorite genres</h2><p>Picked for you and For You lean toward these. Tap to turn a genre on or off.</p>
     <div class="gen" role="group" aria-label="Favorite genres">${genres.map(g=>`<button type="button" data-act="genre" data-g="${esc(g)}" aria-pressed="${S.favGenres.includes(g)}">${S.favGenres.includes(g)?ic("check"):""}${esc(g)}</button>`).join("")}</div></section>
   <section class="card pn" aria-labelledby="s4"><h2 id="s4">Assistant</h2><p>How the assistant uses your data.</p>
     <div class="lockbox">${ic("lock")}<div><b>Read-only.</b> The assistant can read your library, ratings and notes to answer questions. It can never add, change or delete them.</div></div>
     <button class="btn warn sm" data-act="clear-chats">Clear conversation history</button></section>
   <section class="card pn" style="grid-column:1/-1" aria-labelledby="s5"><h2 id="s5">Your data</h2><p>Your library, notes and ratings live only on this computer.</p>
     <div class="row"><button class="btn sm" data-act="export">Export my data (JSON)</button><button class="btn warn sm" data-act="reset">Reset to sample data</button></div></section>
  </div>`;
}

/* ================= assistant chat (read-only) ================= */
function mockAsk(text,bookIsbn){   /* stand-in for UserHandler > Ollama with Kaomoji & personality. FR-27..29 */
  const t=text.toLowerCase(),b=bookIsbn?book(bookIsbn):null;
  const wantsRecs=/recommend|suggest|something|looking for|what should i read|next book|books like|similar|surprise|pick|in the mood|short|under \d+/.test(t);
  const o={};const m=t.match(/under (\d+)/);if(m)o.maxPages=+m[1];else if(/short|quick|weekend/.test(t))o.maxPages=300;
  [["mystery","Mystery"],["fantasy","Fantasy"],["science fiction","Science fiction"],["sci-fi","Science fiction"],["thriller","Thriller"],["romance","Romance"]].forEach(([k,v])=>{if(t.includes(k))o.genre=v});
  ["mythology","survival","isolation","friendship","magic"].forEach(x=>{if(t.includes(x))o.theme=x});
  if(wantsRecs){
    const like=S.books.find(x=>t.includes(x.title.toLowerCase()))||(/like this|similar|this book/.test(t)?b:null);
    let picks;
    if(like)picks=S.books.filter(x=>x.isbn!==like.isbn&&x.status!=="finished"&&x.status!=="progress"&&x.themes.some(z=>like.themes.includes(z))).map(x=>({isbn:x.isbn,why:"Shares "+x.themes.filter(z=>like.themes.includes(z)).map(z=>"#"+z).join(" and ")+" with "+like.title})).slice(0,3);
    else if(/surprise/.test(t)){const p=S.books.filter(x=>x.status==="none");const x=p[Math.floor(Math.random()*p.length)];picks=x?[{isbn:x.isbn,why:"A wild surprise pick outside your shelves (☆▽☆)"}]:[]}
    else picks=recommend(o).slice(0,3).map(r=>({isbn:r.isbn,why:r.why}));
    return{text:picks.length?`Here ${picks.length===1?"is one pick":`are ${picks.length} picks`} based on what you've read and rated (＾▽＾):`:"Nothing in the catalog matches that yet (・_・;). Try a different mood or genre!",picks,used:["Your ratings","Your favorite genres"]};
  }
  if(b){const ns=notesOf(b),a=ns.length?analyze(ns):null;
    if(/theme|about|summar|plot|what is/.test(t))return{text:`${b.title} is a ${b.genres.join(" / ").toLowerCase()} book of ${b.pages} pages (っ˘ω˘ς). Its main themes are ${b.themes.map(z=>"#"+z).join(", ")}.${a&&a.themes.length?` Your own notes touch on ${a.themes.map(z=>"#"+z).join(", ")} (◕‿◕).`:" You haven't written notes on it yet (・_・;)."}`,picks:[],used:["Book summary",ns.length?`Your notes on ${b.title}`:null].filter(Boolean)};
    if(/note|wrote|said/.test(t))return{text:ns.length?`You have ${ns.length} note${ns.length===1?"":"s"} on ${b.title} (◕‿◕)b. The latest says: "${ns[ns.length-1].text}"`:`You haven't written any notes on ${b.title} yet (・_・;).`,picks:[],used:[`Your notes on ${b.title}`]};
    if(/rate|rating|stars/.test(t))return{text:b.rating?`You rated ${b.title} ${b.rating} out of 5 stars (＾▽＾)!`:`You haven't rated ${b.title} yet (・_・;). Its community rating is ${b.avg.toFixed(1)}.`,picks:[],used:["Your rating"]};
    return{text:`${b.title} is ${pct(b)}% read (${b.progress} of ${b.pages} pages) (ง •̀_•́)ง. Ask me about its themes, your notes, or say "suggest something similar" (◕‿◕)!`,picks:[],used:["Your reading progress"]};}
  if(/read|finished|history/.test(t)){const f=S.books.filter(x=>x.status==="finished");return{text:f.length?`You've finished ${f.length} book${f.length===1?"":"s"} so far (＾▽＾)! Keep up the momentum (ง •̀_•́)ง: ${f.map(x=>x.title).join(", ")}.`:"You haven't finished any books yet (っ˘ω˘ς). Time to start your first one!",picks:[],used:["Your library"]}}
  if(/goal|pages|today/.test(t))return{text:`You've read ${pagesToday()} of ${S.goal} pages today, averaging ${avgPerDay()} pages a day this week (⌐■_■).`,picks:[],used:["Your reading log"]};
  return{text:"I can answer questions about your books, notes, and reading habits, and suggest new books whenever you ask (◕‿◕)b. Try \"suggest a short mystery\" or open a book and ask about its themes (っ˘ω˘ς)!",picks:[],used:[]};
}

function mountChat(host,{convId=null,bookIsbn=null,compact=false,onConv}={}){
  let conv=convId?S.convs.find(c=>c.id===convId):null;const msgs=conv?conv.messages:[];const bk=bookIsbn?book(bookIsbn):null;
  host.innerHTML=`<div class="chat ${compact?"cmp":""}"><div class="ro">${ic("lock")}<span>Read-only: the assistant reads your library and notes but never changes them.</span></div>
   ${bk?`<div class="ctxb"><span>Asking about <b>${esc(bk.title)}</b></span><a class="lnk" href="#/assistant" data-act="d-new">Clear</a></div>`:""}
   <div class="msgs" id="msgs${compact?"d":""}" role="log" aria-live="polite"></div>
   <form class="comp"><div class="grow"><label class="sr" for="ci${compact?"d":""}">Message</label><input class="in" id="ci${compact?"d":""}" autocomplete="off" data-limit="${LIMIT}" data-ct="cc${compact?"d":""}" placeholder="${bk?`Ask about ${esc(bk.title)}`:"Tell me what you are in the mood to read"}">${counter("cc"+(compact?"d":""))}</div>
   <button class="go" aria-label="Send">${ic("send")}</button></form></div>`;
  const box=$(".msgs",host),input=$("input",host);
  const hero=()=>`<div class="hero"><h2>What do you feel like reading? (◕‿◕)</h2><p>Describe a mood, a plot, or a book you loved. I'll explain my picks! (っ˘ω˘ς)</p><div class="sug">${(bk?[`What are the themes of this book?`,`What did I write in my notes?`,`Suggest something similar`]:["Something like Project Hail Mary","Suggest a short mystery","What have I finished?","Surprise me"]).map(s=>`<button type="button">${esc(s)}</button>`).join("")}</div></div>`;
  const av=`<span class="av" aria-hidden="true">${ic("spark")}</span>`;
  const draw=typing=>{
    box.innerHTML=(msgs.length||typing?msgs.map(m=>m.role==="user"?`<div class="m u"><div class="bub">${esc(m.text)}</div></div>`
      :`<div class="m b">${av}<div class="bub">${esc(m.text)}${m.picks&&m.picks.length?`<div class="picks">${m.picks.map(k=>{const x=book(k.isbn);return x?`<a class="pk" href="#/book/${x.isbn}" ${compact?'data-act="d-close"':""}>${cover(x)}<div><b>${esc(x.title)}</b><div class="s">${esc(x.author)} · ${x.pages} pages</div><div class="s">${esc(k.why)}</div></div></a>`:""}).join("")}</div>`:""}
      ${m.used&&m.used.length?`<div class="used">Used: ${m.used.map(u=>`<span class="chip">${esc(u)}</span>`).join("")}</div>`:""}</div></div>`).join("")
      +(typing?`<div class="m b ty">${av}<div class="bub">Thinking…</div></div>`:""):hero());
    $$(".sug button",box).forEach(x=>x.addEventListener("click",()=>send(x.textContent)));
    box.scrollTop=box.scrollHeight;
  };
  draw();
  async function send(text){
    text=text.trim();if(!text||text.length>LIMIT)return;
    if(!conv){conv={id:"c"+Date.now(),title:text.slice(0,42),bookIsbn:bookIsbn||undefined,messages:msgs};S.convs.unshift(conv);if(onConv)onConv(conv.id);renderShell()}
    msgs.push({role:"user",text});draw(true);
    await new Promise(r=>setTimeout(r,550));
    try{const r=mockAsk(text,bookIsbn);msgs.push({role:"bot",text:r.text,picks:r.picks,used:r.used})}
    catch(e){msgs.push({role:"bot",text:"The assistant couldn't answer. Check that the local model is running, then try again.",picks:[],used:[]})}
    save();draw();
  }
  $("form",host).addEventListener("submit",e=>{e.preventDefault();const v=input.value;if(v.length>LIMIT)return;input.value="";updateCounter(input);send(v)});
  if(!compact)input.focus();
}

/* ================= drawer ================= */
const drawer={open:false,convId:null,bookIsbn:null};
function openDrawer(o={}){drawer.open=true;if("bookIsbn" in o){drawer.bookIsbn=o.bookIsbn;drawer.convId=null}$("#drawer").classList.add("open");$("#drawer").setAttribute("aria-hidden","false");$("#scrim").classList.add("on");
  mountChat($("#dbody"),{convId:drawer.convId,bookIsbn:drawer.bookIsbn,compact:true,onConv:id=>{drawer.convId=id}});setTimeout(()=>$("#dbody input")?.focus(),230)}
function closeDrawer(){drawer.open=false;$("#drawer").classList.remove("open");$("#drawer").setAttribute("aria-hidden","true");$("#scrim").classList.remove("on");$("#fab").focus()}

/* ================= actions (event delegation) ================= */
const armed=new WeakMap();
function twice(t,label){if(armed.get(t)){armed.delete(t);return true}armed.set(t,1);const old=t.innerHTML;t.classList.add("armed");t.textContent=label;setTimeout(()=>{if(armed.get(t)){armed.delete(t);t.classList.remove("armed");t.innerHTML=old}},3000);return false}
const rerender=()=>{const y=scrollY;route(true);scrollTo(0,y)};
const A={
  async rate(t){
    const isbn=t.dataset.isbn, n=+t.dataset.n;
    const b = (await api.getBook(isbn)) || book(isbn);
    const newRating = b.rating===n?0:n;
    await api.rateBook(isbn, newRating);
    toast(newRating?`Rated ${newRating} of 5`:"Rating cleared");
    rerender();
  },
  async add(t){
    const isbn=t.dataset.isbn;
    await api.addLibrary(isbn);
    const b = (await api.getBook(isbn)) || book(isbn);
    toast(`Added "${b.title}" to your library`);
    renderShell();
    rerender();
  },
  async remove(t){
    if(!twice(t,"Click again to remove"))return;
    const isbn=t.dataset.isbn;
    await api.removeLibrary(isbn);
    toast("Removed from library. Your notes are kept.");
    renderShell();
    rerender();
  },
  "sim-skip"(){
    timeOffset += 1;
    sessionStorage.setItem("sim_time_offset", String(timeOffset));
    toast(`Simulated +1 day (${fmtD(getSimDate())}). No pages read today.`);
    rerender();
  },
  "sim-goal"(){
    const curToday = today();
    S.log[curToday] = (S.log[curToday]||0) + S.goal;
    save();
    timeOffset += 1;
    sessionStorage.setItem("sim_time_offset", String(timeOffset));
    toast(`Logged ${S.goal} pages! Advanced to ${fmtD(getSimDate())}.`);
    rerender();
  },
  "sim-reset"(){
    timeOffset = 0;
    sessionStorage.removeItem("sim_time_offset");
    toast("Reset clock to today");
    rerender();
  },
  reread(t){reread(book(t.dataset.isbn));toast("Started again from page 0");rerender()},
  dismiss(){viewHome.dismissed=true;rerender()},
  "use-goal"(t){S.goal=+t.dataset.n;save();toast(`Daily goal set to ${S.goal} pages`);rerender()},
  more(t){const c=$("#dsc").classList.toggle("cl")===false;t.textContent=c?"Show less":"Show all";t.setAttribute("aria-expanded",c)},
  askbook(t){openDrawer({bookIsbn:t.dataset.isbn})},
  notes(t){const k=t.dataset.isbn;lib.open.has(k)?lib.open.delete(k):lib.open.add(k);rerender()},
  "note-edit"(t){viewBook.editing=t.dataset.id;rerender()},"note-cancel"(){viewBook.editing=null;rerender()},
  "note-del"(t){if(!twice(t,"Confirm delete"))return;const k=t.dataset.isbn;S.notes[k]=notesOf(book(k)).filter(n=>n.id!==t.dataset.id);save();toast("Note deleted");rerender()},
  genre(t){const g=t.dataset.g,i=S.favGenres.indexOf(g);i<0?S.favGenres.push(g):S.favGenres.splice(i,1);save();rerender()},
  "clear-chats"(t){if(!twice(t,"Click again to clear"))return;S.convs=[];drawer.convId=null;save();toast("Conversation history cleared");renderShell()},
  reset(t){if(!twice(t,"Click again to reset"))return;localStorage.removeItem(KEY);S=seed();save();toast("Sample data restored");renderShell();location.hash="#/"},
  export(){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(S,null,2)],{type:"application/json"}));a.download="ai-book-assistant-data.json";a.click();toast("Exported your data")},
  "d-close"(){closeDrawer()},"d-new"(t,e){if(t.tagName==="A")e.preventDefault();drawer.convId=null;drawer.bookIsbn=null;openDrawer({bookIsbn:null})},"d-full"(){const q=drawer.convId?"?c="+drawer.convId:"";closeDrawer();location.hash="#/assistant"+q}
};
document.addEventListener("click",e=>{
  const t=e.target.closest("[data-act]");
  if(!t)return;
  const f=A[t.dataset.act];
  if(f){
    // Don't intercept form submit button clicks that are part of a form submission unless they specify a data-act
    if(t.tagName==="BUTTON" && t.type==="submit" && t.closest("form") && !t.dataset.act.startsWith("d-")) return;
    f(t,e);
  }
});
$("[data-act=d-close]")?.addEventListener("click", (e)=>{ e.preventDefault(); closeDrawer(); });
$("[data-act=d-new]")?.addEventListener("click", (e)=>{ e.preventDefault(); drawer.convId=null; drawer.bookIsbn=null; openDrawer({bookIsbn:null}); });
const F={
  log(f){const b=book(f.dataset.isbn),n=parseInt($("input",f).value);if(!n||n<1)return toast("Enter how many pages you read");const was=b.status;setProgress(b,b.progress+n);toast(b.status==="finished"?`Finished "${b.title}"! Add a rating on its page.`:`Saved ${n} pages`);renderShell();rerender()},
  goal(f){const n=parseInt($("input",f).value);if(!n||n<1)return toast("Enter a goal of at least 1 page");S.goal=Math.min(500,n);save();toast("Daily goal saved");rerender()},
  async pages(f){const isbn=f.dataset.isbn,v=parseInt($("input",f).value); if(isNaN(v)||v<0)return toast("Enter valid page number"); await api.saveProgress(isbn, v);if(isNaN(v)||v<0||v>b.pages)return toast(`Enter a number from 0 to ${b.pages}`);const was=b.status;setProgress(b,v);toast(b.status==="finished"&&was!=="finished"?"Finished! How would you rate it?":"Progress saved");renderShell();rerender()},
  async "note-add"(f){const ta=$("textarea",f),t=ta.value.trim(); if(!t)return toast("Write something first"); if(t.length>LIMIT)return toast("Notes can be up to 3,000 characters"); const isbn=f.dataset.isbn; const kind=$("select",f).value; await api.addNote(isbn, t, kind); toast("Note saved"); rerender(); return;if(!t)return toast("Write something first");if(t.length>LIMIT)return toast("Notes can be up to 3,000 characters");const k=f.dataset.isbn;(S.notes[k]=S.notes[k]||[]).push({id:"n"+Date.now(),type:$("select",f).value,text:t,at:today()});save();toast("Note saved");rerender()},
  "note-save"(f){const t=$("textarea",f).value.trim();if(!t)return toast("A note can't be empty");if(t.length>LIMIT)return toast("Notes can be up to 3,000 characters");const n=notesOf(book(f.dataset.isbn)).find(x=>x.id===f.dataset.id);n.text=t;save();viewBook.editing=null;toast("Note updated");rerender()},
  profile(f){S.name=$("input",f).value.trim()||"Reader";save();renderShell();toast("Profile saved")},
  goals(f){const g=parseInt($("#sg").value),y=parseInt($("#sy").value);if(!g||g<1||!y||y<1)return toast("Goals must be at least 1");S.goal=Math.min(500,g);S.yearGoal=Math.min(200,y);save();toast("Goals saved");rerender()}
};
document.addEventListener("submit",e=>{const f=e.target.closest("[data-form]");if(!f)return;e.preventDefault();F[f.dataset.form]?.(f)});
function updateCounter(t){const c=$("#"+t.dataset.ct);if(!c)return;const n=t.value.length;c.textContent=`${n} / ${LIMIT}`+(n>LIMIT?` · over by ${n-LIMIT}`:"");c.classList.toggle("over",n>LIMIT);
  const btn=t.closest("form")?.querySelector("button:not([type=button])");if(btn)btn.disabled=n>LIMIT}
document.addEventListener("input",e=>{if(e.target.dataset&&e.target.dataset.limit)updateCounter(e.target)});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&drawer.open)closeDrawer()});
$("#scrim").addEventListener("click",closeDrawer);
$("#fab").addEventListener("click",()=>{drawer.bookIsbn=null;openDrawer({})});
$("#gs").addEventListener("submit",e=>{e.preventDefault();goBrowse($("#gq").value,"")});

/* ================= shell + router ================= */
const main=$("#main");
$("#fab").innerHTML=`${ic("spark")} Ask Assistant`;
$("[data-act=d-new]").innerHTML=ic("plus");$("[data-act=d-full]").innerHTML=ic("expand");$("[data-act=d-close]").innerHTML=ic("x");
const NAV=[["home","#/","Home","home"],["library","#/library","My Library","lib"],["browse","#/browse","Browse","search"],["for-you","#/for-you","For You","spark"],["assistant","#/assistant","Assistant","chat"]];
let cur="home";
function renderShell(){
  $("#nav").innerHTML=NAV.map(([k,h,l,i])=>`<a href="${h}" class="${k===cur?"on":""}" ${k===cur?'aria-current="page"':""}>${ic(i)}${l}${k==="library"?`<span class="n">${mine().length}</span>`:""}</a>`).join("");
  $("#av").textContent=(S.name||"R").trim().charAt(0).toUpperCase()||"R";
  $("#fab").hidden=cur==="assistant";
}
const routes=[[/^\/?$/,"home",()=>viewHome()],[/^\/library$/,"library",(m,p)=>viewLibrary(p)],[/^\/browse$/,"browse",(m,p)=>viewBrowse(p)],[/^\/for-you$/,"for-you",(m,p)=>viewForYou(p)],
  [/^\/book\/(\d+)$/,"library",m=>viewBook(m[1])],[/^\/assistant$/,"assistant",(m,p)=>viewAssistant(p)],[/^\/settings$/,"settings",()=>viewSettings()]];
async function route(keep){
  const[path,qs=""]=(location.hash.slice(1)||"/").split("?"),p=new URLSearchParams(qs);
  for(const[re,nav,fn]of routes){const m=path.match(re);if(!m)continue;cur=nav;if(!keep){viewBook.editing=null}renderShell();await fn(m,p);if(!keep){scrollTo(0,0);if(drawer.open)closeDrawer()}document.title=({home:"Home",library:"My Library",browse:"Browse",["for-you"]:"For You",assistant:"Assistant",settings:"Settings"}[nav]||"")+" · AI Book Assistant";return}
  cur="";renderShell();main.innerHTML=`<div class="card empty">Page not found. <a class="lnk" href="#/">Go home</a></div>`;
}
/* Load the real catalogue and library state from the database when the backend is running.
   Falls back to the built-in sample books when it is not. */
async function loadBooksFromApi(){
  try{
    if(!(await api.checkBackend())) return;
    const res = await fetch(`${API_BASE}/api/books?limit=2000`);
    if(!res.ok) return;
    const rows = await res.json();
    if(Array.isArray(rows) && rows.length) S.books = rows;
  }catch(e){ console.warn("Could not load books from database:", e); }
}
window.addEventListener("hashchange",()=>route());
loadBooksFromApi().then(()=>route());

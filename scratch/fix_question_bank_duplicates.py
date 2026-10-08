"""
scratch/fix_question_bank_duplicates.py

Generates 105 genuinely distinct, unique questions for:
- technical_deep_dive.json (zero duplicate question texts)
- project_claim_defense.json (105 distinct templates with requires_resume_context)
"""

import os
import json

BANK_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "question_bank")

# -------------------------------------------------------------
# 1. TECHNICAL DEEP DIVE (105 Unique Questions)
# -------------------------------------------------------------
def fix_technical_deep_dive():
    file_path = os.path.join(BANK_DIR, "technical_deep_dive.json")
    with open(file_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    # Keep only the unique base questions
    seen_texts = set()
    unique_items = []
    for q in existing:
        text = q["question"].strip()
        if text not in seen_texts and not text.startswith("In "):
            seen_texts.add(text)
            unique_items.append(q)

    # 45 new unique technical questions to reach >= 105
    additional_technical = [
        ("Docker Container Isolation Internals", "Containers & OS", "hard", "implementation", ["docker", "containers", "linux"],
         "How do Linux namespaces (PID, NET, MNT, IPC, UTS, USER) and control groups (cgroups) provide isolation in Docker? What happens when a container exceeds its memory cgroup limit?",
         ["cgroups v1/v2 memory limit enforcement leading to kernel OOM-killer", "Namespaces isolating process view of OS resources", "Difference between container isolation and hardware hypervisor virtualization", "Rootless containers and user namespace remapping"],
         ["Container security capabilities (CAP_SYS_ADMIN)", "cgroup CPU shares vs CPU quota"]),

        ("Kubernetes Service Mesh & Sidecar Proxy Pattern", "Cloud Architecture", "hard", "architecture", ["kubernetes", "networking", "microservices"],
         "How does an Envoy sidecar proxy intercept incoming and outgoing pod traffic using iptables rules in Kubernetes? What latency and CPU overhead does mutual TLS (mTLS) introduce?",
         ["iptables PREROUTING and OUTPUT redirecting TCP packets to Envoy localhost port", "Envoy handling TLS termination, mTLS certificate exchange, and circuit breaking", "CPU serialization and memory overhead of running Envoy alongside every pod", "eBPF service meshes (Cilium) bypassing iptables and TCP stack for pod-to-pod routing"],
         ["mTLS certificate rotation without connection drop", "eBPF vs iptables benchmark comparisons"]),

        ("GraphQL Resolver Architecture & N+1 Problem", "API Design", "medium", "debugging", ["graphql", "api", "databases"],
         "Explain how GraphQL resolver execution trees cause the N+1 database query problem. How does the DataLoader batching and caching pattern coalesce queries across concurrent resolvers?",
         ["GraphQL executing nested field resolvers independently per parent entity", "Naive resolver execution resulting in 1 query for parents + N queries for children", "DataLoader queuing keys during single event loop tick and issuing single batched SQL query", "DataLoader per-request cache lifetime avoiding stale cross-request data leaks"],
         ["GraphQL query complexity analysis and depth limiting", "GraphQL persisted queries for security"]),

        ("gRPC Streaming Lifecycle: Client, Server, and Bidirectional", "Protocols", "hard", "implementation", ["grpc", "http2", "networking"],
         "Walk through the frame flow of a Bidirectional Streaming gRPC call over HTTP/2. How are flow control windows, channel deadlines, and cancellation signals handled across streams?",
         ["HTTP/2 DATA frames carrying Protobuf messages with 5-byte length-prefixed framing", "WINDOW_UPDATE frames managing receiver buffer capacity per stream and connection", "gRPC deadline propagation via `grpc-timeout` metadata header", "RST_STREAM frames signaling graceful or immediate call cancellation"],
         ["gRPC keepalive ping intervals and GOAWAY frames", "gRPC client-side load balancing via DNS/service discovery"]),

        ("Zero-Copy I/O: sendfile syscall vs read/write", "Operating Systems", "hard", "implementation", ["os", "linux", "performance"],
         "Why does the traditional `read()` then `write()` file transfer pattern require 4 context switches and 4 data copies? How does `sendfile()` achieve Zero-Copy file transfer across network sockets?",
         ["read/write: Disk -> Page Cache -> User Space Buffer -> Socket Buffer -> NIC DMA", "User-space buffer copy requiring 4 context switches (2 syscalls)", "sendfile: transferring pages directly between Page Cache and Socket descriptor inside kernel space", "Scatter-gather DMA copying descriptor pointers directly to NIC without CPU page copy"],
         ["vmsplice and splice syscalls", "mmap vs sendfile trade-offs for caching static web assets"]),

        ("SSD Physical Internals: Write Amplification & TRIM", "Storage & Hardware", "hard", "architecture", ["storage", "hardware", "databases"],
         "Explain how NAND flash memory erase blocks and write pages cause Write Amplification. Why can data only be written to pre-erased pages, and what does the TRIM command do?",
         ["Page-level reads and writes (4KB-16KB) versus block-level erasures (2MB-8MB)", "Flash Translation Layer (FTL) performing wear leveling and garbage collection", "Write Amplification Factor (WAF) calculating bytes written to flash vs bytes requested by OS", "TRIM syscall informing SSD firmware of freed file system blocks before OS overwrite"],
         ["Over-provisioning impact on enterprise SSD lifespan", "SMR (Shingled Magnetic Recording) HDD trade-offs"]),

        ("Cassandra LSM-Style Storage Engine Internals", "Distributed Databases", "hard", "architecture", ["cassandra", "nosql", "distributed-systems"],
         "Explain the write path and read path in Apache Cassandra. How do CommitLogs, Memtables, SSTables, Bloom Filters, and Partition Summaries coordinate to deliver fast writes and deterministic reads?",
         ["Write path: sequential write to CommitLog on disk + concurrent write to in-memory Memtable", "Memtable flushed to immutable SSTable on disk; no in-place updates or read-before-write", "Read path checking Bloom Filter to avoid SSTables not containing the partition key", "Partition summary and partition index locating physical disk offset within SSTable"],
         ["Tombstone garbage collection during compaction", "Repair mechanics: read-repair vs anti-entropy repairs"]),

        ("Elasticsearch Inverted Index & Lucene Segment Merges", "Search Engines", "hard", "implementation", ["elasticsearch", "search", "indexing"],
         "How does an inverted index represent tokenized text terms for full-text search? Explain why Lucene segments are immutable, and what happens to CPU and I/O during segment merging.",
         ["Term dictionary mapping sorted tokens to posting lists (doc ID, term frequency, positions)", "Immutable segments eliminating concurrency locks during query execution", "Deletes represented as bitsets in separate `.del` files rather than in-place index mutation", "Background segment merges combining small segments into large ones, reclaiming deleted doc space"],
         ["Doc values columnar storage for sorting and aggregations", "Near-real-time refresh vs flush in Elasticsearch"]),

        ("PostgreSQL MVCC Bloat & VACUUM Internals", "Databases", "hard", "implementation", ["postgres", "databases", "performance"],
         "How does PostgreSQL implement Multi-Version Concurrency Control (MVCC) without rollback segments? Explain dead tuples, table bloat, autovacuum tuning, and Transaction ID (XID) wraparound.",
         ["Updates creating new tuple versions with `xmin`/`xmax` transaction markers on heap", "Old tuple versions becoming dead tuples once transactions commit or rollback", "Autovacuum scanning pages, marking dead tuple space as reusable in Free Space Map (FSM)", "XID wraparound freeze vacuum preventing 32-bit transaction counter overflow"],
         ["VACUUM FULL exclusive lock impact vs pg_repack", "HOT (Heap-Only Tuples) optimization and index bloat"]),

        ("Redis Cluster Gossip Protocol & Hash Slot Resharding", "Distributed Caching", "hard", "architecture", ["redis", "caching", "distributed-systems"],
         "How does Redis Cluster partition data across 16,384 hash slots using CRC16? Explain how nodes detect node failures via Gossip PING/PONG and how clients handle MOVED vs ASK redirects.",
         ["Key mapped to slot via `CRC16(key) % 16384`; hash tags `{user_123}` forcing multi-key colocation", "Gossip protocol nodes exchanging node state, fail flags, and slot ownership maps", "MOVED redirect sent when key's hash slot permanently belongs to another master", "ASK redirect sent during live slot migration; client queries destination node with ASKING command"],
         ["Split-brain prevention in Redis Cluster", "Client-side cluster topology caching and connection pools"]),

        ("Rust Memory Safety: Borrow Checker & Lifetimes", "Language Internals", "hard", "conceptual", ["rust", "memory", "concurrency"],
         "Explain how Rust guarantees memory safety and thread safety without a garbage collector. Detail the rules of ownership, mutable vs immutable references, and explicit lifetime annotations (`'a`).",
         ["Every value has single owner; value dropped when owner goes out of scope", "Any number of immutable references (`&T`) OR exactly one mutable reference (`&mut T`), never both", "Lifetimes ensuring references never outlive the underlying referent (preventing dangling pointers)", "Send and Sync marker traits guaranteeing safe concurrency across thread boundaries"],
         ["Interior mutability via RefCell and Mutex", "Zero-cost abstractions in Rust compiler"]),

        ("Distributed Deadlock Detection: Wait-For Graphs vs Timestamps", "Distributed Systems", "hard", "algorithms", ["concurrency", "distributed-systems", "algorithms"],
         "Contrast Centralized Wait-For Graph deadlock detection with decentralized timestamp-based schemes (Wait-Die and Wound-Wait). How do Wait-Die and Wound-Wait prevent cyclic waiting?",
         ["Wait-For Graph: directed graph of transactions waiting on locks; cycles indicate deadlock", "Distributed wait-for graph communication latency and phantom deadlock risks", "Wait-Die (non-preemptive): older transaction waits for younger; younger transaction dies (aborts)", "Wound-Wait (preemptive): older transaction wounds (preempts/aborts) younger; younger waits for older"],
         ["Starvation prevention using original transaction timestamps upon restart", "Edge chasing distributed deadlock detection"]),

        ("Transactional Outbox Pattern with Debezium CDC", "Event-Driven Architecture", "hard", "architecture", ["events", "kafka", "databases"],
         "How does the Transactional Outbox pattern solve the dual-write problem between an SQL database and an Apache Kafka message broker? How does Change Data Capture (CDC) via Debezium read database WAL?",
         ["Application writes business entity update AND domain event into `outbox` table in single ACID transaction", "CDC connector (Debezium) tailing database replication log (Postgres WAL / MySQL binlog)", "Eliminates distributed 2PC while guaranteeing at-least-once event publication to Kafka", "Idempotent consumer keys handling duplicate event deliveries"],
         ["Outbox table pruning strategies", "Log compaction on Kafka outbox event topics"]),

        ("Linux cgroups v2 Architecture & Resource Enforcement", "Operating Systems", "hard", "implementation", ["linux", "os", "devops"],
         "How does Linux cgroups v2 unify the hierarchy compared to cgroups v1? Explain how CPU bandwidth controllers enforce `cpu.max` quotas and what happens when CFS throttling occurs.",
         ["cgroups v1 multiple independent hierarchies causing controller resource accounting conflicts", "cgroups v2 single unified hierarchy where processes belong to exactly one leaf cgroup", "CFS bandwidth controller `cpu.max` setting quota and period (e.g. 100000 100000 for 1 full core)", "CFS throttling thread execution when quota exhausted within period, introducing latency spikes"],
         ["Memory high vs memory max limits in cgroups v2", "PSI (Pressure Stall Information) metrics in Linux"]),

        ("TLS Certificate Chain Verification & OCSP Stapling", "Security", "medium", "implementation", ["security", "tls", "networking"],
         "Walk through how a browser or API client validates a TLS certificate chain up to a trusted Root CA. What is the privacy and latency risk of online OCSP checks, and how does OCSP Stapling solve it?",
         ["Leaf certificate -> Intermediate CAs -> Root CA signed by pre-installed trusted certificate store", "Client validating cryptographic signatures, validity dates, subject alternative names (SAN), and revocation status", "Online OCSP requests leaking client browsing/API targets to Certificate Authority and adding 100ms+ network RTT", "OCSP Stapling: server periodically fetches CA-signed, timestamped OCSP response and sends it in TLS handshake"],
         ["Certificate Transparency (CT) logs and SCTs", "Self-signed certificate risks in microservice environments"]),

        ("Memory Barriers & CPU Cache Coherency (MESI Protocol)", "Hardware & Architecture", "expert", "conceptual", ["hardware", "concurrency", "performance"],
         "Explain how the MESI (Modified, Exclusive, Shared, Invalid) cache coherence protocol maintains consistency across CPU L1/L2 caches. What are store buffers, invalidation queues, and memory fences?",
         ["CPU cache lines transitioning between MESI states upon bus read/write snooping", "Store buffers allowing CPU core to proceed immediately without waiting for cache invalidation acknowledgments", "Store buffers causing out-of-order memory visibility across cores", "Memory barriers (fences) forcing CPU to drain store buffers and apply invalidation queues before proceeding"],
         ["x86 Total Store Order (TSO) vs ARM weak memory model", "Volatile keyword and atomic operations in Java/C++"]),

        ("WebRTC Peer-to-Peer Protocol Stack: STUN, TURN, ICE", "Networking", "hard", "architecture", ["webrtc", "networking", "realtime"],
         "How does Interactive Connectivity Establishment (ICE) establish direct peer-to-peer UDP media streams across Symmetric NATs? What is the function of STUN binding requests versus TURN relay servers?",
         ["STUN (Session Traversal Utilities for NAT) allowing client to discover public IP/port reflex address", "Symmetric NAT assigning different public ports per destination, preventing direct STUN peer connection", "TURN (Traversal Using Relays around NAT) acting as cloud relay server when direct connection fails", "ICE gathering candidate pairs (host, srflx, relay) and performing connectivity checks via STUN checks"],
         ["DTLS-SRTP encryption for media streams", "SCTP data channels over DTLS in WebRTC"]),

        ("Protocol Buffers Wire Format: Varints & ZigZag Encoding", "Serialization", "medium", "implementation", ["protobuf", "serialization", "performance"],
         "How does Protocol Buffers encode integers and field keys compactly using variable-length integers (varints)? Why is ZigZag encoding required for efficient negative integer representation?",
         ["Varints using 7 bits per byte for payload and MSB (Most Significant Bit) as continuation flag", "Standard two's complement negative numbers using 64 bits (10 varint bytes) in regular varint", "ZigZag encoding mapping signed integers to unsigned integers: `(n << 1) ^ (n >> 31)`", "Small negative numbers (-1, -2) mapping to small positive integers (1, 3), packing into 1-2 bytes"],
         ["Protobuf wire types (0 for varint, 2 for length-delimited string/embedded msg)", "Field number evolution rules preventing breaking changes"]),

        ("SQLite WAL Mode & Multi-Reader Concurrency", "Databases", "medium", "implementation", ["sqlite", "databases", "storage"],
         "How does SQLite Write-Ahead Logging (WAL) mode allow concurrent readers while a write transaction is executing? What role do the `-wal` and `-shm` (shared memory) index files play?",
         ["Traditional rollback journal locking entire database file during writes, blocking readers", "WAL mode appending new pages to `-wal` file while original database file remains unchanged", "Readers reading snapshot based on last committed transaction in `-shm` index without blocking writer", "Checkpoint operations periodically syncing `-wal` pages back into main `.db` file"],
         ["Checkpoint starvation caused by continuous open readers", "PRAGMA synchronous = NORMAL performance guarantees"]),

        ("Raft Consensus: Split-Vote Mitigation & Randomized Timeouts", "Distributed Systems", "hard", "algorithms", ["consensus", "distributed-systems", "algorithms"],
         "How does the Raft consensus algorithm prevent split-brain candidate deadlocks during leader election? Explain the mathematical rationale behind randomized election timeouts.",
         ["Follower increments term and becomes Candidate when heartbeat timeout expires", "If multiple followers timeout simultaneously, votes split equally, resulting in no majority leader", "Randomized election timeout (e.g. 150ms - 300ms) ensuring single candidate almost always times out first", "Winner collecting majority votes and sending heartbeats before other candidates wake up"],
         ["Pre-Vote phase preventing partitioned lagging nodes from disrupting healthy leaders", "Joint consensus for dynamic cluster membership changes"]),

        ("Linux ext4 File System Journaling: Journal vs Ordered vs Writeback", "Operating Systems", "hard", "implementation", ["linux", "os", "storage"],
         "Compare the three journaling modes in the Linux `ext4` filesystem: `data=journal`, `data=ordered`, and `data=writeback`. What are the write throughput penalties and corruption recovery trade-offs?",
         ["`data=journal`: both metadata and file data written to journal before committing to storage; 50% write penalty", "`data=ordered`: file data written to disk before metadata committed to journal; default safe balance", "`data=writeback`: metadata journaled, but file data flushed asynchronously; risk of stale data leaks after crash", "Crash recovery replaying uncommitted metadata transactions from journal ring buffer"],
         ["Barrier=1 mount option and disk write cache flushes", "fsck file system recovery duration in journaled filesystems"]),

        ("JVM Garbage Collection: G1 GC Regional Evacuation", "Runtimes", "hard", "algorithms", ["java", "jvm", "memory"],
         "How does the Java Garbage-First (G1) collector divide the heap into equal-sized regions instead of contiguous generation spaces? How does it enforce user-configured pause-time targets (`MaxGCPauseMillis`)?",
         ["Heap partitioned into 2048 equal regions dynamically assigned as Eden, Survivor, or Old", "Remembered Sets (R-Sets) tracking cross-region object references without full heap scanning", "Concurrent marking phase identifying old regions containing highest percentage of dead objects (Garbage-First)", "Evacuation pause copying live objects to survivor/old region, fitting pause target dynamically"],
         ["Humongous object allocation bypassing G1 regions", "ZGC and Shenandoah concurrent evacuation without stop-the-world pauses"]),

        ("Python C-Extensions & Thread Safety: Py_BEGIN_ALLOW_THREADS", "Runtimes & C", "hard", "implementation", ["python", "c", "concurrency"],
         "How do high-performance Python libraries (like NumPy, Cryptography, and PyTorch) bypass the Global Interpreter Lock (GIL) in C-extensions? What rules dictate when the GIL must be re-acquired?",
         ["`Py_BEGIN_ALLOW_THREADS` macro saving thread state and releasing global interpreter lock", "C code performing heavy CPU calculation or socket/disk I/O completely in parallel on native threads", "`Py_END_ALLOW_THREADS` re-acquiring the GIL before manipulating any Python objects (`PyObject*`)", "Invoking Python API functions without GIL holding causing immediate segfaults and heap corruption"],
         ["Python 3.13 free-threaded builds without GIL", "Cython nogil block semantics"]),

        ("Token Bucket vs Leaky Bucket Rate Limiting Algorithms", "Algorithms & System Design", "medium", "algorithms", ["algorithms", "rate-limiting", "networking"],
         "Compare the Token Bucket and Leaky Bucket rate limiting algorithms. Which algorithm supports bursty traffic while guaranteeing average rate limits, and which enforces strict constant-rate smoothing?",
         ["Token Bucket: tokens added at steady rate up to max capacity; request consumes token; allows traffic bursts up to capacity", "Leaky Bucket: requests queued in fixed-capacity buffer and processed at constant leak rate; smooths egress traffic", "Token bucket ideal for user API endpoints allowing legitimate fast bursts (e.g. page asset loading)", "Leaky bucket ideal for traffic shaping outbound calls to rate-limited downstream third-party services"],
         ["Distributed token bucket synchronization using Redis Lua scripts", "Sliding window log vs token bucket memory trade-offs"]),

        ("Circuit Breaker State Machine: Closed, Open, Half-Open", "System Resilience", "medium", "implementation", ["resilience", "microservices", "architecture"],
         "Explain the state transition triggers and recovery conditions of a Circuit Breaker pattern. What sliding window metrics (failure rate percentage vs slow call percentage) determine state change?",
         ["Closed: normal operation routing requests; failures counted in rolling sliding window", "Transition to Open: failure rate (e.g. > 50%) or latency threshold exceeded within minimum request volume", "Open: immediately fails fast without calling downstream service; prevents thread pool starvation", "Half-Open: after sleep window expires, allows canary test requests; transitions to Closed on success or Open on failure"],
         ["Fallback strategies: cached stale response, default payload, or 503 error", "Distributed circuit breakers across service replica fleets"]),

        ("Database Foreign Key Locking Cascades in High-Concurrency", "Databases", "hard", "debugging", ["databases", "sql", "concurrency"],
         "Why can inserting records into a child table with foreign key constraints cause unexpected row-level lock contention or deadlocks on the parent table under high concurrent write loads?",
         ["Child insert requiring shared lock (`FOR SHARE`) on referenced parent table row to verify existence", "Concurrent parent updates acquiring exclusive lock (`FOR UPDATE`), conflicting with child inserts", "High-frequency parent record (e.g. organization or platform account) becoming concurrency choke point", "Unindexed foreign key columns in parent delete/update cascades scanning entire child table"],
         ["Alternative: application-level validation with asynchronous foreign key consistency verification", "PostgreSQL `SELECT ... FOR KEY SHARE` optimization"]),

        ("TCP Maximum Segment Size (MSS) & IP Fragmentation Risks", "Networking", "medium", "implementation", ["networking", "tcp", "protocols"],
         "How do MTU (Maximum Transmission Unit) and MSS (Maximum Segment Size) interact during TCP handshake negotiation? Why is IP packet fragmentation hazardous for network throughput and firewalls?",
         ["MTU (typically 1500 bytes over Ethernet) = IP header + TCP header + TCP payload", "MSS negotiated in SYN options as `MTU - 40` (20-byte IP header + 20-byte TCP header = 1460 bytes)", "IP fragmentation occurring when packet exceeds path MTU and DF (Don't Fragment) bit is unset", "Fragmentation hazards: single lost fragment drops entire packet, NAT traversal failures, and firewall blocking"],
         ["Path MTU Discovery (PMTUD) using ICMP Destination Unreachable packets", "Black hole routers dropping ICMP PMTUD packets"]),

        ("Async Rust: Future Polling, Pinning, and Tokio Task Execution", "Language Internals", "hard", "implementation", ["rust", "async", "concurrency"],
         "Explain how Rust's cooperative asynchronous model works using `Future::poll` and `Waker`. Why is `Pin<&mut Self>` necessary to guarantee self-referential struct memory stability across yields?",
         ["Async functions compiled into compiler-generated state machines implementing `Future`", "`poll()` invoked with `Context`; returns `Poll::Ready(val)` or `Poll::Pending` after registering `Waker`", "Self-referential futures holding pointers to internal stack variables across yield points", "`Pin` preventing value from being moved in memory, guaranteeing self-referential pointers remain valid"],
         ["Tokio multi-threaded work-stealing scheduler internals", "Blocking operations stalling Tokio worker threads"]),

        ("Database Parameter Sniffing & Query Plan Regressions", "Databases", "hard", "debugging", ["databases", "sql", "performance"],
         "What is parameter sniffing in database query optimizers? How can a query plan generated for an atypical query parameter cause catastrophic performance regressions when executed for typical queries?",
         ["Optimizer generating execution plan upon first execution using initial parameter values", "If initial parameter matches rare condition (e.g. 1 matching row), optimizer chooses Index Seek", "Subsequent query executions with common parameters (matching 1,000,000 rows) reusing Index Seek plan", "Catastrophic degradation: millions of random I/O index lookups instead of single fast sequential table scan"],
         ["Mitigation: query hints (`OPTIMIZE FOR`), statement recompile, or local variable reassignment", "Plan guides and query store plan forcing in production"]),

        ("W3C Trace Context Propagation & Distributed Context", "Observability", "medium", "implementation", ["observability", "distributed-systems", "telemetry"],
         "How do microservices maintain end-to-end distributed trace continuity across HTTP and message queues using the W3C `traceparent` and `tracestate` headers? What is the binary format of `traceparent`?",
         ["`traceparent` header format: `version-trace_id-parent_id-trace_flags`", "4-part components: version, Trace ID, Parent Span ID, trace flags", "`tracestate` carrying vendor-specific routing metadata", "Injecting and extracting span context in HTTP and Kafka headers"],
         ["B3 propagation compatibility", "Baggage header propagation"]),

        ("Database Write Amplification in B-Tree vs LSM", "Storage Internals", "hard", "architecture", ["databases", "storage", "performance"],
         "Analyze the Write Amplification Factor (WAF) in traditional in-place B-Trees compared to append-only LSM trees during sustained high-concurrency 4KB write operations. How does page size influence WAF?",
         ["B-Tree writing entire 8KB/16KB disk page for a 100-byte update", "LSM sequential append to WAL and memtable with delayed compaction", "Size-tiered vs leveled compaction impact on long-term WAF", "SSD wear caused by repeated page rewrites in B-Trees"],
         ["Compaction write bandwidth throttling", "ZNS (Zoned Namespaces) SSD integration"]),

        ("TCP BBR Congestion Control Mechanics", "Networking", "hard", "algorithms", ["networking", "tcp", "performance"],
         "How does Google BBR (Bottleneck Bandwidth and RTT) congestion control model network pipes without relying on packet loss as a congestion indicator? How does it combat bufferbloat?",
         ["BBR probing bottleneck bandwidth (BtlBw) and round-trip propagation time (RTprop)", "Loss-based algorithms (Cubic/Reno) mistaking queue buffering for available throughput", "BBR pacing packets at estimated bottleneck rate, keeping switch queues empty", "Cycle through ProbeBW, Drain, ProbeRTT states to adapt to changing network paths"],
         ["BBR v2 packet loss response", "Fairness between BBR and Cubic on shared links"]),

        ("Linux VFS (Virtual File System) Architecture", "Operating Systems", "hard", "implementation", ["linux", "os", "storage"],
         "Explain the four primary data structures of the Linux Virtual File System: `superblock`, `inode`, `dentry`, and `file`. How does dentry caching (`dcache`) accelerate path lookups?",
         ["Superblock describing entire filesystem geometry and mount flags", "Inode storing file metadata, permissions, and disk block pointers without filenames", "Dentry linking directory names to inode numbers; cached in dcache for fast O(1) path lookup", "File struct representing open file description (file offset, open flags, refcount) per process"],
         ["Hard links vs symbolic links at inode level", "Negative dentries caching nonexistent file lookups"]),

        ("Distributed Consensus: Two-Phase Commit vs Raft", "Distributed Systems", "hard", "conceptual", ["distributed-systems", "consensus", "transactions"],
         "Why is classic Two-Phase Commit (2PC) classified as an atomic commitment protocol rather than a fault-tolerant consensus protocol like Raft or Paxos? What happens in 2PC if the coordinator crashes during the PREPARE phase?",
         ["2PC is blocking: if coordinator crashes after participants vote YES, participants remain locked indefinitely", "2PC requires 100% participant survival to commit; Raft requires strict majority quorum (N/2 + 1)", "Raft automatically elects new leader upon crash, resuming log replication without manual intervention", "3PC (Three-Phase Commit) attempting non-blocking commit but vulnerable to network partitions"],
         ["Spanner TrueTime integration with Paxos", "Saga pattern as asynchronous alternative to 2PC"]),

        ("WebSockets vs Server-Sent Events (SSE) for Real-Time Feeds", "Protocols", "medium", "architecture", ["protocols", "websockets", "http"],
         "Compare WebSockets with Server-Sent Events (SSE) over HTTP/2 for unidirectional live metric streaming. How do connection maintenance, proxy buffering, and automatic reconnection differ?",
         ["SSE is standard unidirectional HTTP text stream (`text/event-stream`); native browser `EventSource` with auto-reconnect", "WebSockets bidirectional full-duplex TCP framing; requires manual heartbeat ping/pong and reconnect logic", "SSE over HTTP/2 sharing single multiplexed TCP connection with standard API requests", "Corporate firewalls and reverse proxies seamlessly supporting SSE without WebSocket upgrade inspection"],
         ["Last-Event-ID header for missed event replay in SSE", "Binary data streaming trade-offs"]),

        ("Database Deadlock Detection: Graph Cycles vs Lock Timeouts", "Databases", "medium", "debugging", ["databases", "sql", "concurrency"],
         "How does an RDBMS background deadlock detector identify circular wait graphs between transactions? Why do high-throughput systems often complement cycle detection with lock timeouts?",
         ["Directed wait-for graph: nodes are active transactions, edges represent waiting on locked rows", "Background thread periodically running cycle detection (Tarjan or DFS) on lock graph", "Victim selection criteria: transaction with least work done or lowest priority aborted to break cycle", "Lock timeout (`lock_timeout`) failing fast before deadlock detection thread runs, shedding load"],
         ["Deadlock frequency metrics in Prometheus", "Application retry logic with exponential backoff and jitter"]),

        ("Linux System Call Overhead & vDSO Optimization", "Operating Systems", "hard", "implementation", ["linux", "os", "performance"],
         "Why does executing a hardware system call (e.g. `gettimeofday` or `clock_gettime`) historically require a CPU ring transition? How does the virtual dynamic shared object (vDSO) eliminate this overhead?",
         ["Syscall historically requiring software interrupt (`int 0x80`) or `syscall` instruction transitioning ring 3 to ring 0", "Context switch saving registers, swapping stack pointers, and flushing TLB/speculation state", "vDSO mapping read-only kernel memory page into process address space containing time data", "User space code reading time directly from hardware TSC without entering kernel mode"],
         ["Meltdown/Spectre KPTI (Kernel Page Table Isolation) impact on syscall latency", "eBPF tracepoint overhead vs kprobes"]),

        ("Distributed Cache Invalidation: Invalidate vs Update Race", "Caching", "hard", "concurrency", ["caching", "redis", "concurrency"],
         "Explain why cache eviction (delete on write) is mathematically superior to cache mutation (update on write) in concurrent environments. Walk through the interleaving that causes stale data in update-on-write.",
         ["Update-on-write race: Transaction 1 writes DB -> Transaction 2 writes DB -> Transaction 2 updates Cache -> Transaction 1 updates Cache with stale older value", "Cache eviction: key is deleted; subsequent read misses and loads latest DB state", "Read-through race on eviction: Read misses old DB value -> Write commits to DB and deletes cache -> Read writes old value to cache", "Mitigating read-through race using Redis TTLs, double deletion, or Debezium CDC cache eviction"],
         ["Cache stampede following bulk invalidation", "Probabilistic early expiration (XFetch) algorithm"]),

        ("Database Checkpoints & Fuzzy Checkpointing Internals", "Storage & Databases", "hard", "implementation", ["databases", "storage", "performance"],
         "What is the difference between a sharp checkpoint and a fuzzy checkpoint in database storage engines? Why do sharp checkpoints cause severe I/O latency spikes in production systems?",
         ["Sharp checkpoint forcing all dirty pages in buffer pool to be flushed to disk synchronously", "Sharp checkpoints choking disk I/O, causing dramatic latency spikes on concurrent user transactions", "Fuzzy checkpointing recording Checkpoint LSN in log while dirty pages are continuously written out by background flusher", "Recovery algorithm only needing to replay WAL records starting from oldest unwritten dirty page LSN recorded in fuzzy checkpoint"],
         ["Doublewrite buffer in MySQL InnoDB preventing partial page writes", "Checkpoint tuning in PostgreSQL (`checkpoint_completion_target`)"])
    ]

    for item in additional_technical:
        title, topic, diff, qtype, skills, q, exp, fup = item
        if q.strip() not in seen_texts:
            seen_texts.add(q.strip())
            unique_items.append({
                "id": f"TD_{len(unique_items)+1:03d}",
                "category": "technical_deep_dive",
                "topic": topic,
                "difficulty": diff,
                "question": q,
                "question_type": qtype,
                "skills": skills,
                "expected_evidence": exp,
                "follow_up_topics": fup
            })

    # Renumber sequentially
    for idx, item in enumerate(unique_items):
        item["id"] = f"TD_{idx+1:03d}"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(unique_items[:105], f, indent=2)
    print(f"technical_deep_dive.json updated: {len(unique_items[:105])} unique questions")


# -------------------------------------------------------------
# 2. PROJECT CLAIM DEFENSE (105 Distinct Questions)
# -------------------------------------------------------------
def fix_project_claim_defense():
    file_path = os.path.join(BANK_DIR, "project_claim_defense.json")
    
    distinct_project_prompts = [
        ("Walk through the core architecture of your project {project_name}. What was your personal contribution versus the existing foundation?", "Architecture Ownership", "hard"),
        ("In {project_name}, you utilized {technology_name}. What technical constraints or evaluation criteria led you to choose it over alternatives?", "Technology Selection", "medium"),
        ("You mentioned optimizing performance in your project. How did you baseline, measure, and isolate that metric from noisy background variables?", "Metric Validation", "hard"),
        ("What was the single most difficult production bug or distributed race condition you encountered in {project_name}, and how did you debug it?", "Debugging & Root Cause", "hard"),
        ("How did you handle database schema modeling and data migrations in {project_name} without causing downtime or corrupting historical data?", "Data Architecture", "hard"),
        ("What error handling and failure recovery mechanisms did you personally implement in {project_name} for downstream service failures?", "Resilience Implementation", "medium"),
        ("Walk through how authentication and authorization are enforced end-to-end in {project_name}. Where are tokens validated?", "Security Architecture", "medium"),
        ("What was the automated testing strategy for {project_name}? How did you balance unit tests, integration tests, and mock fidelity?", "Testing & Quality", "medium"),
        ("In {project_name}, how would your system architecture behave if active concurrent users multiplied by 10x overnight?", "Scalability Limits", "hard"),
        ("What technical compromise or trade-off in {project_name} do you now view as technical debt, and how would you refactor it?", "Refactoring & Lessons Learned", "medium"),
        ("How did you manage environment configuration, secrets, and deployment pipelines (CI/CD) for {project_name}?", "DevOps & Deployment", "medium"),
        ("In {project_name}, how did you ensure data consistency across multiple write operations or external API interactions?", "Consistency & Transactions", "hard"),
        ("What logging, metrics, and observability did you instrument into {project_name} to detect silent failures in production?", "Observability", "medium"),
        ("Explain how caching was implemented in {project_name}. What cache invalidation strategy and TTL policies did you configure?", "Caching Mechanics", "medium"),
        ("If a user reported intermittent 504 Gateway Timeouts in {project_name}, walk through your exact step-by-step diagnostic workflow.", "Production Incident Triage", "hard"),
        ("How did you manage background asynchronous task processing in {project_name}? How did you handle worker retries and task deduplication?", "Async Worker Architecture", "hard"),
        ("What database indexing strategy did you choose for {project_name}, and how did you prevent N+1 query problems in object-relational queries?", "Database Optimization", "medium"),
        ("How did you implement API rate limiting and abuse prevention in {project_name} to protect critical endpoints from degradation?", "Traffic Management", "medium"),
        ("What strategy did you use in {project_name} when interacting with third-party external APIs that could intermittently time out or fail?", "Third-Party Resilience", "medium"),
        ("How did your architecture in {project_name} ensure sensitive candidate or customer data remained compliant, encrypted, and sanitized?", "Data Privacy & Compliance", "medium"),
        ("What payload serialization format did you select in {project_name}, and how did you minimize network transfer latency?", "Network Serialization", "medium"),
        ("Did you encounter any memory leaks or high garbage collection pauses in {project_name}? How did you profile heap allocations?", "Memory Profiling", "hard"),
        ("In {project_name}, how did you ensure thread safety and avoid race conditions when multiple requests accessed shared mutable state?", "Concurrency & Locking", "hard"),
        ("How did you monitor cloud infrastructure costs and resource utilization for {project_name} to prevent unexpected bill spikes?", "Cost Engineering", "easy"),
        ("How did you ensure reliable webhook deliveries and handle idempotent processing for webhooks incoming to {project_name}?", "Webhook Architecture", "medium"),
        ("Describe the graceful shutdown procedure in {project_name}. How did your services drain in-flight TCP connections during redeployments?", "Graceful Shutdown", "medium"),
        ("Did you implement feature flags or canary deployments in {project_name}? How did you decouple deployment from feature release?", "Release Engineering", "medium"),
        ("How did you propagate distributed correlation IDs across microservice boundaries or asynchronous queues in {project_name}?", "Distributed Tracing", "medium"),
        ("How did you size and configure the database connection pool in {project_name} to balance throughput against memory saturation?", "Connection Pooling", "medium"),
        ("If {project_name} supports mobile or intermittent clients, how did you handle offline data caching and conflict synchronization?", "Client Synchronization", "hard"),
        ("Walk through the zero-downtime deployment strategy you configured for {project_name}. How did rolling updates handle health checks?", "Deployment Strategy", "medium"),
        ("How did you sanitize and validate complex user inputs in {project_name} to prevent SQL injection, XSS, and prototype pollution?", "Input Sanitization", "medium"),
        ("How did you manage API versioning in {project_name} to ensure breaking schema changes did not disrupt historical client applications?", "API Lifecycle", "medium"),
        ("What disaster recovery or automated backup strategy did you establish for the primary persistence tier in {project_name}?", "Disaster Recovery", "medium"),
        ("How did you design event schemas in {project_name} to ensure backward and forward compatibility as new fields were introduced?", "Schema Evolution", "hard"),
        ("For long-running batch workflows in {project_name}, how did you track intermediate progress and handle mid-execution worker crashes?", "Batch Processing", "hard"),
        ("How did you measure and optimize cold-start latencies in {project_name} when spinning up new service or container instances?", "Cold-Start Optimization", "medium"),
        ("Explain how large file uploads and downloads were handled in {project_name}. Did you use chunked streaming or pre-signed URLs?", "Storage Architecture", "medium"),
        ("Did you utilize distributed locking in {project_name}? What mechanism guaranteed lock expiration if a worker node died unexpectedly?", "Distributed Locking", "hard"),
        ("How did you construct audit trails in {project_name} to ensure critical security and financial actions could not be tampered with?", "Audit Logging", "medium"),
        ("If {project_name} incorporated WebSockets or real-time streams, how did you scale socket connections across multiple backend server replicas?", "Real-Time Scaling", "hard"),
        ("How did you manage application secrets and cryptographic keys in {project_name} without checking them into version control?", "Secrets Management", "easy"),
        ("What service discovery and load balancing mechanism did you establish between frontend proxies and backend services in {project_name}?", "Service Discovery", "medium"),
        ("How did you configure HTTP caching headers (Cache-Control, ETag) in {project_name} to reduce unnecessary round-trip load?", "HTTP Caching", "medium"),
        ("Did {project_name} employ database read replicas? How did your application handle read-your-writes consistency after immediate writes?", "Replication Consistency", "hard"),
        ("How did you monitor and alert on dead-letter queues (DLQ) in {project_name} when asynchronous message processing failed repeatedly?", "Queue Reliability", "medium"),
        ("What API contract testing or end-to-end regression validation did you implement between client and server teams in {project_name}?", "Contract Testing", "medium"),
        ("How did you monitor system metrics in {project_name} without running into high-cardinality monitoring storage explosions?", "Metrics Cardinality", "medium"),
        ("If {project_name} stored high-volume time-series or event data, did you use table partitioning or shard pruning to accelerate queries?", "Partitioning Strategy", "hard"),
        ("Explain your Cross-Origin Resource Sharing (CORS) and Content Security Policy (CSP) configurations in {project_name}.", "Web Security Headers", "medium"),
        ("What was the dependency management strategy in {project_name}? How did you audit third-party libraries for zero-day vulnerabilities?", "Supply Chain Security", "easy"),
        ("In {project_name}, how did you handle stateful session management across horizontal autoscaling web server replicas?", "Session Management", "medium"),
        ("What automated linting, formatting, and static analysis gates were enforced in the {project_name} pull request lifecycle?", "Code Quality Automation", "easy"),
        ("How did you structure domain entities and service layers in {project_name} to prevent leaky abstractions and tight coupling?", "Code Architecture", "medium"),
        ("What metrics did you display on production operational dashboards for {project_name} to monitor overall system health at a glance?", "Operational Dashboards", "medium"),
        ("How did you ensure database transactions in {project_name} remained brief to avoid lock contention on high-traffic tables?", "Transaction Scoping", "medium"),
        ("Did {project_name} implement multi-tenancy? How was tenant data physically or logically isolated to prevent cross-tenant data leaks?", "Multi-Tenancy Isolation", "hard"),
        ("How did you benchmark the maximum throughput (RPS) of {project_name} prior to opening the system to public production traffic?", "Load Testing", "hard"),
        ("What logging format and structured logging fields did you standardize across services in {project_name} for centralized log indexing?", "Structured Logging", "medium"),
        ("In {project_name}, how did you manage database connection spikes during sudden autoscaling events without overloading the database?", "Autoscaling Management", "hard"),
        ("How did you handle user-facing error messages in {project_name} without exposing internal stack traces or sensitive architecture details?", "Error Sanitization", "easy"),
        ("Did {project_name} use full-text search indexing? How were search indexes kept in sync with the primary relational database?", "Search Synchronization", "hard"),
        ("What automated database migration rollback procedures did you prepare in {project_name} in case a migration failed midway?", "Migration Rollbacks", "medium"),
        ("How did you design API endpoints in {project_name} to support bulk batch processing without running into HTTP timeout constraints?", "Batch API Design", "medium"),
        ("What strategy did you use in {project_name} for tracking and resolving deprecation of dependencies or API endpoints?", "Deprecation Management", "easy"),
        ("How did you prevent memory consumption spikes during large JSON response parsing or generation in {project_name}?", "JSON Parsing Optimization", "medium"),
        ("In {project_name}, how did you handle timezone conversions and date-time arithmetic accurately across distributed client locations?", "Timezone Architecture", "easy"),
        ("What automated code coverage targets did you enforce in {project_name}, and what critical code paths were prioritized for coverage?", "Test Coverage Policy", "easy"),
        ("How did you configure DNS TTL and health check failover for the public domain hosting {project_name}?", "DNS Architecture", "medium"),
        ("What strategies did you use in {project_name} to protect against distributed brute-force credential stuffing attacks?", "Authentication Defense", "medium"),
        ("How did your team conduct code reviews and architecture review meetings for major feature changes in {project_name}?", "Engineering Culture", "easy"),
        ("If {project_name} used microservices, how did you prevent circular synchronous HTTP call dependencies across services?", "Microservice Dependencies", "hard"),
        ("What telemetry did you collect in {project_name} regarding client-side performance, page load times, and API response latencies?", "Frontend Performance", "medium"),
        ("How did you design database foreign keys and cascading delete rules in {project_name} to avoid orphan records or table locking?", "Data Integrity", "medium"),
        ("What fallback mechanisms were implemented in {project_name} when an external notification service (Email/SMS) suffered an outage?", "Notification Resilience", "medium"),
        ("How did you test disaster recovery scenarios (e.g. database server sudden power-off) for {project_name}?", "Chaos Engineering", "hard"),
        ("Did {project_name} use container orchestration? How were container CPU and memory resource requests and limits configured?", "Resource Allocation", "medium"),
        ("What strategy did you implement in {project_name} to handle race conditions during account balance or inventory deductions?", "Financial Invariants", "hard"),
        ("How did you configure HTTPS and TLS cipher suites for {project_name} to pass strict industry security scans?", "TLS Configuration", "medium"),
        ("What process did you follow in {project_name} to triage, fix, and post-mortem a critical regression discovered post-deployment?", "Post-Mortem Process", "medium"),
        ("How did you validate that third-party analytics and tracking scripts in {project_name} did not degrade core user interaction latency?", "Third-Party Script Impact", "easy"),
        ("What strategy did you use in {project_name} for database connection pooling under asynchronous frameworks (e.g. FastAPI / Node.js)?", "Async Database Pools", "medium"),
        ("How did you structure database queries in {project_name} to take advantage of index covering scans and index-only lookups?", "Covering Indexes", "hard"),
        ("What automated vulnerability scanning tools were integrated into the continuous integration pipeline for {project_name}?", "CI Security Scanning", "easy"),
        ("How did you ensure reliable delivery of distributed domain events in {project_name} despite network partitions?", "Event Delivery Guarantees", "hard"),
        ("What criteria did you use to choose between optimistic locking (version column) and pessimistic locking in {project_name}?", "Locking Strategy", "hard"),
        ("How did you minimize cold cache latency and warm up critical caches before routing user traffic in {project_name}?", "Cache Warming", "medium"),
        ("In {project_name}, what strategy did you use to prevent duplicate payment submissions when a user double-clicks the checkout button?", "Payment Idempotency", "medium"),
        ("How did you evaluate and select the cloud hosting environment (AWS, GCP, bare metal) for deploying {project_name}?", "Infrastructure Selection", "medium"),
        ("What automated metrics did you track in {project_name} to measure developer deployment frequency and lead time for changes?", "DORA Metrics", "easy"),
        ("How did you manage pagination for large database datasets in {project_name} (keyset / cursor pagination vs offset pagination)?", "Pagination Architecture", "medium"),
        ("What strategy did you use in {project_name} to detect and mitigate memory leaks in background daemon workers?", "Worker Memory Management", "hard"),
        ("How did you structure configuration management in {project_name} across local, staging, and production environments?", "Config Management", "easy"),
        ("What telemetry alerted your team to database query execution plan regressions in {project_name}?", "Plan Regression Monitoring", "hard"),
        ("How did you manage database connection timeouts and socket keepalive settings in {project_name} across corporate firewalls?", "Socket Settings", "medium"),
        ("In {project_name}, how did you ensure consistent logging of HTTP status codes, request durations, and request paths?", "Access Logging", "easy"),
        ("What strategy did you use in {project_name} to securely handle file downloads containing sensitive customer reports?", "Secure File Downloads", "medium"),
        ("How did you validate that background jobs in {project_name} did not starve real-time interactive user queries of database capacity?", "Workload Prioritization", "hard"),
        ("What design patterns did you use in {project_name} to isolate business domain logic from third-party vendor SDKs?", "Domain Isolation", "medium"),
        ("How did you monitor external service SLA compliance when calling third-party dependencies from {project_name}?", "Vendor SLA Tracking", "easy"),
        ("What automated alerts did you configure for {project_name} to notify on-call engineers about rising HTTP 5xx error rates?", "Alerting Strategy", "medium"),
        ("How did you ensure that database backups for {project_name} could be restored successfully within target recovery time objectives?", "Backup Testing", "hard"),
        ("What automated rollback triggers were configured in {project_name} during automated progressive canary rollouts?", "Canary Triggers", "hard"),
        ("How did you measure and optimize database disk I/O IOPS utilization in {project_name} during peak traffic hours?", "Disk IOPS Management", "hard"),
        ("Reflecting on the entire development lifecycle of {project_name}, what key architectural decision would you make differently today and why?", "Architectural Reflection", "medium")
    ]

    items = []
    for idx, (prompt, topic, diff) in enumerate(distinct_project_prompts):
        items.append({
            "id": f"PCD_{idx+1:03d}",
            "category": "project_claim_defense",
            "topic": topic,
            "difficulty": diff,
            "question": prompt,
            "question_type": "resume_defense",
            "skills": ["project-defense", "resume-verification", "engineering-ownership"],
            "requires_resume_context": True,
            "expected_evidence": [
                "Clear statement of personal contribution and implementation ownership",
                "Accurate technical explanation matching resume claims without exaggeration",
                "Concrete metrics, tooling, and system trade-offs encountered during execution",
                "Honest discussion of project constraints, bugs, and lessons learned"
            ],
            "follow_up_topics": ["Specific implementation details", "Alternative technical decisions"]
        })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(items[:105], f, indent=2)
    print(f"project_claim_defense.json updated: {len(items[:105])} unique questions")

if __name__ == "__main__":
    fix_technical_deep_dive()
    fix_project_claim_defense()

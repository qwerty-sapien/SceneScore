# Independent evaluated-geometry review

Status: **06 V4 and final repaired 08 V3 pass the scoped evaluated static-geometry gate. Earlier failed candidates are preserved.**

This review did not author the mechanics or Blender scenes. Input copies and SHA256 bindings are retained under `inputs/` and in each result JSON. The scripts import no project geometry or physics implementation. Six independent plane/edge/intersection controls passed before the BVH audit ran.

## 06 — evaluated V2

All 7,201 replay poses were checked. The sphere and finite torus use an enclosing sphere; the cylinder uses a world-Y capsule with endpoints ±0.15 m. Radius is inflated to 0.2400004 m to cover evaluated radius, scale and axle roundoff. Actual sphere/cylinder/torus dimensions and axle orientation match the declared models; details are in `LEAD-SHAPES-06-v2.json`.

Own side rails and uprights were excluded only after independently measuring their separating Y planes against the actual body support envelope at every pose. Worst numerical halfspace overlap is 0.000348 mm. This is an explicit contact allowance, not an exclusion of arbitrary nearby scenery.

The own floor's Y-extrusion geometry was independently verified, allowing exact centre-segment swept-sphere distance to cover the cylinder's axial capsule too. Maximum conservative swept-floor intrusion is 0.005322 mm for the sphere, 0.013734 mm for the cylinder and 0.007709 mm for the torus. All satisfy the coordinator's 0.2 mm penetration target.

Every other static triangle, including support caps, other lanes, backstops and checkpoint lamps, remained separated. Conservative bounds over the complete intervals between adjacent replay keys are 27.623 mm, 3.837 mm and 27.831 mm respectively. The closest sampled cylinder capsule-to-lamp clearance is 6.192 mm. Inter-key bounds use the distance function's 1-Lipschitz property and reserve half each interval's full translation plus a roundoff allowance.

Result: `RESULTS-06-v2.json`. This result may bind a later shader-only version only after byte identity of evaluated geometry and replay states is established. Moving receivers remain a separate explicit-pose/source-gap check owned by the integrator. This does not establish full-motion visual acceptance.

V3 was audited directly because fresh Blender UV-sphere triangulation changed some faces despite unchanged vertex coordinates. `RESULTS-06-v3.json` binds the V3 inputs. It independently passes the same scope: maximum swept-floor intrusion 0.013734 mm and minimum other-static inter-key lower bound 3.837098 mm. No evaluated-geometry byte identity is claimed.

Final V4 changes the hoop-coil material for visibility and was also audited directly. `RESULTS-06-v4.json` binds evaluated geometry SHA256 `1270a7450364beac63863473ad92de6165c18e8f06504ca4968b02d7e01eae4f`; measured clearance values are unchanged. `LEAD-SHAPES-06-v4.json` records actual lead shape metrics and confirms byte identity of mechanics states, replay states and packet against V3. Evaluated geometry bytes differ and were independently tested. V4 passes this scoped static-geometry gate.

## 08 — preserved V1 failure

The independent BVH covered 12,856 guide triangles and 1,348 other static triangles, at every replay pose and throughout all 7,200 straight translation segments between keys. Euclidean point/segment-to-triangle distances were computed directly from evaluated local vertices and exported poses.

At 20.469867 s, the conservative bead overlaps `observatory-guide-left`, triangle 650, by **31.015390 mm**. A separate closest-edge calculation confirms the witness. The evaluated bead's inscribed radius is 0.238751026 m; therefore the wall reaches at least **29.766416 mm inside the rendered bead**, even allowing its 1.248974 mm faceting deficit. This is not a false positive caused by using the analytic radius.

The offending edge is an internal triangulation diagonal across a tall, twisted wall quad. Source centreline/Jacobian controls did not certify that actual triangulated surface. `V1-WITNESS.json` contains the centre, exact world triangle, nearest edge point and projection checks. The plane projection falls outside the triangle; the validated witness is the closest edge point.

Other static surfaces clear by at least 27.822471 mm over the complete replay intervals. Sampled moving-plunger overlap is only 0.000070 mm. These passing components do not override the wall failure.

Result: `RESULTS-v1.json`. The repair must be tested on new raw packet surfaces and then the newly evaluated Blender mesh, preserving the failed V1 evidence and the computed motion/event identities.

## 08 — repaired raw V3, pre-Blender

The replacement uses explicit triangles and adaptive stations. The independent audit covered 266,980 guide/capture triangles and 4,340 other static triangles, with no omitted static shapes. Quad faces were conservatively tested under both diagonals. Exact canonical state and event hashes match the supplied baseline (`338562a9…a9f81` and `5ee8f5ee…9d819`).

Maximum sampled sphere overlap is 0.019704 mm, so the large twisted-wall defect is resolved in these raw surfaces. However, the full linear replay sweep reaches **0.227643 mm** into `observatory-capture-rail`, face 54542, at **22.623056547 s**, between ticks 5429 and 5430. This exceeds the unchanged 0.2 mm target by 0.027643 mm. The result is a conservative sphere bound, not yet proof of actual faceted-bead penetration. Key-to-key chord sag is a plausible contributor; the witness is recorded for a bounded geometric repair or an exact rendered-bead follow-up.

Other static surfaces, including uprights and rail feet, clear by at least 23.797796 mm over the complete replay intervals. `RAW-08-repaired-v3.json` and `RAW-V3-WITNESS.json` preserve the measurements; the exact raw packet is frozen under `inputs/08-raw-repaired-v3/`. This is pre-Blender evidence and does not certify a later evaluated mesh.

## 08 — final repaired raw V5, pre-Blender

The coordinator approved a disclosed 60 µm outward contact-skin allowance. Adaptive stations and the 30 µm contact-plane tessellation budget were retained; the mechanics and event sequences remain exactly unchanged. `RAW-V5-MECHANICS-IDENTITY.json` independently confirms deep equality against the original V1 mechanics-state file and packet events. This allowance changes the rendered contact surface within a declared numerical approximation; it does not enter the mechanics.

All 7,201 sample centres and 7,200 linear swept intervals were checked against 266,980 guide/capture triangles and 4,340 other static triangles. No static shape was omitted. The sphere radius was inflated to 0.240001 m to reserve an additional 1 µm before actual Blender geometry is measured.

Worst conservative swept intrusion is **0.168644 mm**, at **22.623056516 s** on `observatory-capture-rail`, face 54542. Minimum sampled guide clearance is **+0.039296 mm**. Other static surfaces have at least **23.856793 mm** clearance over the complete replay intervals. This passes the unchanged **0.2 mm** raw-surface target.

`RAW-08-repaired-v5.json` binds packet SHA256 `80fa90ba477c25610176377ad315b0e8737de5633b60ad4f988ca6cb11ea4b53`, frozen under `inputs/08-raw-repaired-v5/`, and the exact audit-script hashes. This remains pre-Blender evidence; the final evaluated mesh must be checked separately.

## 08 — final evaluated Blender V3

The final Blender candidate `08_spiral_observatory-v3` was tested directly. Its evaluated geometry SHA256 is `9193a045acb429e06a5f39b8278f74f7b9f9bb59da9ea643f815fe83459d8253`; replay-state SHA256 is `086c3d6454ec14b5cc592ab8d352fee0f9d5731a43095516edc8ce1a6bb0c05c`. Exact input copies are preserved under `inputs/08_spiral_observatory-v3/`.

The independent audit covered all 266,980 guide/capture triangles and 3,316 other evaluated static triangles at every one of 7,201 poses and throughout all 7,200 linear replay intervals. The lower other-static count than the raw audit comes from testing the actual Blender triangulation instead of both possible diagonals of raw quads. No static object was excluded. All packet mesh IDs were present with matching vertex counts; the maximum corresponding vertex discrepancy is **0.200187 µm**, on the floor.

The evaluated bead's maximum local vertex radius is 0.240000262856495 m. Scale is exactly `[1,1,1]` and its quaternion exactly `[0,0,0,1]` at all 7,201 samples. The audit used an enclosing radius of **0.240001262856495 m**, adding a further **1 µm** replay numerical reserve. It does not depend on the bead's coarser faceting to obtain a pass.

Worst conservative swept guide intrusion is **0.168883 mm**, at **22.623056538 s**, on `observatory-capture-rail`, triangle 54542, between ticks 5429 and 5430. Minimum sampled guide clearance is **+0.039021 mm**. Every other static surface clears by at least **23.856539 mm** throughout the complete replay intervals. The final evaluated geometry therefore passes the unchanged **0.2 mm** target.

Moving receiver checks are separate: the evaluated plunger OBB's worst sampled conservative intrusion is **1.333 µm**, including the 1 µm reserve, at 24.779167 s; the moving coil's enclosing OBB has at least **50.432154 mm** sampled clearance. These receiver measurements cover all replay samples but do not claim an independent inter-sample moving-OBB sweep.

`FINAL-08-V3-MECHANICS-IDENTITY.json` confirms that both mechanics-state and replay-state files are byte-identical to V1, and events are deeply equal with the unchanged canonical event hash. `FINAL-08-V3-BEAD-SHAPE.json` records constant scale/orientation and verifies root `rolling.py` SHA256 `5d8741f0116ded2c628461a08efffd4ae81a9267795e62fc4b3a5ea337f054fa`. `RESULTS-08-final-evaluated-v3.json` binds the complete measurements and audit-script hash.

This closes the requested static mesh and declared-shape review for the exact final 06 V4 and 08 V3 candidates. Full-motion perception, musical integration and human approval remain separate gates owned by their respective reviewers.

## Execution and limits

`audit_meshes.py`: PID/PGID 61613, exit 0, 15.765 s. `audit_six.py`: PID/PGID 72160, exit 0, 17.799 s. Both were single-process, dependency-free Python analyses with 150-second alarms. `AUDIT-TEARDOWN-1.json` records precise process absence checks. No Blender, browser, server or rendering process was started by this review.

Repaired raw V3 audit: PID/PGID 79972, exit 0, 74.715 s. Direct 06 V3 audit: PID/PGID 80277, exit 0, 17.874 s. `AUDIT-TEARDOWN-2.json` confirms both exact PIDs absent.

Final 06 V4 audit: PID/PGID 82000, exit 0, 15.966 s. `AUDIT-TEARDOWN-3.json` confirms that exact PID absent.

The first raw V5 attempt, PID/PGID 89075, exited 1 on its 150-second runtime cap at tick 5400 under concurrent load. It produced no complete geometry result; `RAW-V5-ATTEMPT-1.json` records the incomplete attempt and confirms process absence. One repeat used a 300-second cap with the same distance calculation and geometry target: PID/PGID 94490, exit 0, 257.009 s. `AUDIT-TEARDOWN-4.json` confirms that exact PID absent.

Final evaluated 08 V3 audit: PID/PGID 66013, session 24567, exit 0, 67.715 s under a 300-second cap. `AUDIT-TEARDOWN-5.json` confirms that exact PID absent. All review-owned jobs have exited; no persistent task resource remains.

The signed quantity is centre-to-surface distance minus a conservative body radius. It detects surface overlap; it is not a general signed-distance-field implementation for arbitrary unknown closed meshes. Exact sampled or swept scopes, exclusions and moving-receiver limits are stated above. Shape faceting, physical controls, evaluated replay, full-motion perception and human approval remain distinct evidence.

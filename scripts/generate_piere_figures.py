"""Generate ten publication figures (PNG, SVG, PDF) from saved PIERE results."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = {
    "fixed_15": "#64748b", "fixed_35": "#2563eb", "fixed_webster": "#7c3aed",
    "vehicle_actuated": "#ea580c", "queue_based": "#16a34a", "queue_based_legacy": "#94a3b8",
}
LABELS = {
    "fixed_15": "Fixed 15 s", "fixed_35": "Fixed 35 s", "fixed_webster": "Webster",
    "vehicle_actuated": "Vehicle actuated", "queue_based": "Queue based", "queue_based_legacy": "Queue based legacy",
}
CONTROLLERS = list(LABELS)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 11, "figure.titlesize": 13})


def read(name: str) -> dict:
    return json.loads((ROOT / "outputs" / name).read_text(encoding="utf-8"))


def merged(horizon: int) -> tuple[pd.DataFrame, list[dict]]:
    base = read(f"piere_revision_{horizon}.json")
    add = read(f"piere_revision_addendum_{horizon}.json")
    return pd.DataFrame(base["summary"] + add["summary"]), base["runs"] + add["runs"]


def save(fig: plt.Figure, number: int, name: str) -> None:
    fig.set_size_inches(max(7.1, fig.get_figwidth()), max(4.1, fig.get_figheight()))
    fig.tight_layout()
    stem = OUT / f"figure_{number:02d}_{name}"
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    svg_path = stem.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight")
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def fig1() -> None:
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    boxes = [(0.3, 1.5, 2.2, 1.1, "Intersection image\n(test or upload)"),
             (3.0, 1.5, 2.2, 1.1, "YOLO count by\napproach"),
             (5.7, 1.5, 1.8, 1.1, "Initial queues\nqN, qS, qE, qW"),
             (8.0, 1.5, 1.7, 1.1, "SimPy phase\ncontrol model")]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",fc="#eff6ff",ec="#2563eb",lw=1.5))
        ax.text(x+w/2,y+h/2,label,ha="center",va="center")
    for x in (2.55,5.25,7.55):
        ax.annotate("",xy=(x+0.4,2.05),xytext=(x,2.05),arrowprops={"arrowstyle":"->","lw":1.5})
    ax.text(5,3.35,"Image-based initial state and discrete-event phase control",ha="center",weight="bold")
    ax.text(8.8,0.8,"Fixed 15 / 35 · Webster · vehicle-actuated · queue-based",ha="center",fontsize=8)
    ax.text(8.8,0.35,"Outputs: waiting · integral queue · throughput · residual queue · phase trace",ha="center",fontsize=8)
    save(fig,1,"system_architecture")


def fig2() -> None:
    path=ROOT/"paper"/"figures"/"perception_example_test_06.jpg"
    image=plt.imread(path)
    fig,ax=plt.subplots(); ax.imshow(image); ax.axis("off")
    ax.set_title("YOLO11 detections and approach-specific vehicle counts")
    save(fig,2,"yolo_example")


def fig3() -> None:
    summary,_=merged(3600); data=summary[summary.controller.isin(CONTROLLERS[:5])]
    scenarios=["symmetric","asymmetric_ns","variable_demand","sudden_dominance_switch","high_load","symmetric_low","symmetric_9","asymmetric_ew","true_oversaturated"]
    titles={
        "symmetric":"Symmetric 6/min", "asymmetric_ns":"Asymmetric N/S 10/4",
        "variable_demand":"Variable demand", "sudden_dominance_switch":"Dominance switch",
        "high_load":"High load 18/min", "symmetric_low":"Symmetric 3/min",
        "symmetric_9":"Symmetric 9/min", "asymmetric_ew":"Asymmetric E/W 4/10",
        "true_oversaturated":"Oversaturated 24/min",
    }
    fig,axes=plt.subplots(3,3,sharey=False,figsize=(7.1,6.6))
    for ax,scenario in zip(axes.flat,scenarios,strict=True):
        part=data[data.scenario==scenario].set_index("controller").reindex(CONTROLLERS[:5]).dropna(subset=["average_wait_seconds"])
        x=np.arange(len(part)); colors=[COLORS[c] for c in part.index]
        ax.bar(x,part.average_wait_seconds,color=colors,yerr=part.wait_95ci_half_width,capsize=2)
        ax.set_xticks(x,[LABELS[c] for c in part.index],rotation=45,ha="right",fontsize=7)
        ax.set_title(titles[scenario]); ax.set_ylabel("Mean wait (s)"); ax.grid(axis="y",alpha=.2)
    fig.suptitle("Controller comparison at 3600 s (mean ± 95% t interval)")
    save(fig,3,"controller_comparison")


def fig4() -> None:
    payload=read("piere_revision_3600.json"); scenario="symmetric"; fig,ax=plt.subplots()
    for controller in CONTROLLERS[:5]:
        run=next(r for r in payload["runs"] if r["scenario"]==scenario and r["seed"]==101 and r["controller"]==controller)
        ax.plot(np.arange(0,len(run["queue_series"]),30)/60,np.array(run["queue_series"])[::30],label=LABELS[controller],color=COLORS[controller])
    ax.set(xlabel="Time (min)",ylabel="Vehicles waiting",title="Queue dynamics, symmetric demand, seed 101 (common arrivals)")
    ax.legend(ncol=2); ax.grid(alpha=.2); save(fig,4,"queue_dynamics_paired")


def fig5() -> None:
    payload=read("piere_revision_3600.json"); fig,axes=plt.subplots(5,1,sharex=True)
    color_map={"green":"#16a34a","yellow":"#facc15","red":"#dc2626"}
    for ax,controller in zip(axes,CONTROLLERS[:5],strict=True):
        run=next(r for r in payload["runs"] if r["scenario"]=="symmetric" and r["seed"]==101 and r["controller"]==controller)
        events=run["phase_history"]; end=600
        for i,event in enumerate(events):
            start=float(event["at"]); stop=min(float(events[i+1]["at"]) if i+1<len(events) else end,end)
            if start>=end: break
            ax.barh(0,stop-start,left=start,height=.6,color=color_map.get(event["color"],"#888"),edgecolor="none")
        ax.set_yticks([]); ax.set_ylabel(LABELS[controller],rotation=0,ha="right",va="center"); ax.grid(axis="x",alpha=.2)
    axes[-1].set_xlabel("Time (s), first 600 s"); fig.suptitle("Signal phase traces, symmetric demand, seed 101")
    save(fig,5,"phase_traces")


def fig6() -> None:
    summary,_=merged(3600); fig,axes=plt.subplots(1,2,sharey=True)
    for ax,scenario,title in zip(axes,["asymmetric_ns","asymmetric_ew"],["N/S dominant","E/W dominant"],strict=True):
        part=summary[(summary.scenario==scenario)&summary.controller.isin(CONTROLLERS[:5])].set_index("controller").reindex(CONTROLLERS[:5])
        x=np.arange(5); ax.bar(x,part.average_wait_seconds,color=[COLORS[c] for c in CONTROLLERS[:5]],yerr=part.wait_95ci_half_width,capsize=3)
        ax.set_xticks(x,[LABELS[c] for c in CONTROLLERS[:5]],rotation=45,ha="right"); ax.set_title(title); ax.set_ylabel("Mean wait (s)"); ax.grid(axis="y",alpha=.2)
    fig.suptitle("Directional asymmetry and mirrored demand (3600 s)"); save(fig,6,"asymmetric_demand")


def fig7() -> None:
    payload=read("piere_revision_3600.json"); fig,ax=plt.subplots()
    for controller in CONTROLLERS[:5]:
        runs=[r for r in payload["runs"] if r["scenario"]=="sudden_dominance_switch" and r["controller"]==controller]
        series=np.mean(np.array([r["queue_series"] for r in runs]),axis=0)
        ax.plot(np.arange(0,len(series),30)/60,series[::30],label=LABELS[controller],color=COLORS[controller])
    ax.axvline(15,color="#111827",ls="--",lw=1,label="Demand shift at 15 min")
    ax.set(xlabel="Time (min)",ylabel="Mean waiting queue (vehicles)",title="Response to a sudden dominant-axis change")
    ax.legend(ncol=2); ax.grid(alpha=.2); save(fig,7,"demand_shift_response")


def fig8() -> None:
    payload=read("piere_perception_sensitivity_expanded.json"); rows=[r for r in payload["summary"] if r["controller"]=="queue_based"]
    frame=pd.DataFrame(rows); frame["rate"]=frame.scenario.str.rsplit("_",n=1).str[-1].str.replace("pct","",regex=False).astype(float)
    frame["regime"]=frame.scenario.str.rsplit("_",n=1).str[0]
    regimes=list(frame.regime.drop_duplicates()); fig,axes=plt.subplots(3,2,figsize=(7.1,6.2))
    for ax,regime in zip(axes.flat,regimes,strict=False):
        part=frame[frame.regime==regime].sort_values("rate")
        ax.errorbar(part.rate,part.average_wait_seconds,yerr=part.wait_95ci_half_width,marker="o",capsize=2,color="#2563eb")
        ax.set_title(regime.replace("_"," ")); ax.set_xlabel("Observation error (%)"); ax.set_ylabel("Mean wait (s)"); ax.grid(alpha=.2)
    axes.flat[-1].axis("off"); fig.suptitle("Synthetic perception error sensitivity (queue-based controller)")
    save(fig,8,"perception_sensitivity")


def fig9() -> None:
    payload=json.loads((ROOT/"computer-vision"/"evaluation_results.json").read_text(encoding="utf-8"))
    lanes=["north","south","east","west"]; gt=[]; pred=[]
    for lane in lanes:
        gt.append(sum(r["directions"][lane]["actual"] for r in payload["images"]))
        pred.append(sum(r["directions"][lane]["predicted"] for r in payload["images"]))
    x=np.arange(4); fig,ax=plt.subplots(); ax.bar(x-.18,gt,.36,label="Reference counts",color="#2563eb"); ax.bar(x+.18,pred,.36,label="YOLO counts",color="#16a34a")
    ax.set_xticks(x,[s.title() for s in lanes]); ax.set_ylabel("Vehicle count across 16 images"); ax.set_title("Directional count evaluation (VisDrone checkpoint)"); ax.legend(); ax.grid(axis="y",alpha=.2)
    save(fig,9,"detector_directional_counts")


def fig10() -> None:
    summary,runs=merged(3600); scenarios=["high_load","true_oversaturated"]
    data=summary[(summary.scenario.isin(scenarios))&summary.controller.isin(CONTROLLERS[:5])]
    residual=[]
    for scenario in scenarios:
        for controller in CONTROLLERS[:5]:
            chosen=[r["waiting_at_end"] for r in runs if r["scenario"]==scenario and r["controller"]==controller]
            residual.append({"scenario":scenario,"controller":controller,"residual":np.mean(chosen)})
    frame=pd.DataFrame(residual); fig,axes=plt.subplots(1,3,figsize=(8.0,3.8))
    for ax,metric,title in zip(axes,["average_wait_seconds","average_queue_length","residual"],["Completed-vehicle wait (s)","Mean queue (vehicles)","Vehicles waiting at T"],strict=True):
        source=data if metric!="residual" else frame
        value="average_wait_seconds" if metric!="residual" else "residual"
        for i,scenario in enumerate(scenarios):
            part=source[source.scenario==scenario].set_index("controller").reindex(CONTROLLERS[:5])
            ax.plot(np.arange(5)+i*.12,part[value],"o",label="18/min" if scenario==scenarios[0] else "24/min")
        ax.set_xticks(np.arange(5)+.06,[LABELS[c] for c in CONTROLLERS[:5]],rotation=55,ha="right",fontsize=6); ax.set_ylabel("Seconds" if metric=="average_wait_seconds" else "Vehicles"); ax.set_title(title,fontsize=9); ax.grid(axis="y",alpha=.2)
    axes[0].legend(); fig.suptitle("Overload: departures-only wait and end-of-run censoring")
    save(fig,10,"overload_and_censoring")


def main() -> None:
    for fn in (fig1,fig2,fig3,fig4,fig5,fig6,fig7,fig8,fig9,fig10): fn()
    print(f"Wrote 30 publication files to {OUT}")

if __name__ == "__main__": main()

import { useEffect, useState } from "react";
import { ApiError, api, type Animation, type ApproachView, type InputParam } from "../api";
import { InputEditor } from "../input/InputEditor";
import { AnimationView } from "../player/AnimationView";

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: Animation };

// The step-by-step player for one verified approach, plus the learner's own inputs.
export function ApproachPlayer({
  problemId,
  approach: a,
  inputs,
}: {
  problemId: string;
  approach: ApproachView;
  inputs: InputParam[];
}) {
  const [animation, setAnimation] = useState<Load>({ status: "loading" });
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .approachAnimation(problemId, a.id)
      .then((data) => !cancelled && setAnimation({ status: "ok", data }))
      .catch((e: Error) => !cancelled && setAnimation({ status: "error", message: e.message }));
    return () => {
      cancelled = true;
    };
  }, [problemId, a.id]);

  const defaults = a.default_input?.args ?? [];
  const shown = animation.status === "ok" ? animation.data.input.args : defaults;

  async function run(args: unknown[]) {
    setRunning(true);
    try {
      const data = await api.customApproachAnimation(problemId, a.id, args);
      setAnimation({ status: "ok", data });
      return null;
    } catch (err) {
      if (err instanceof ApiError) return { message: err.message, issues: err.issues };
      return { message: "Couldn't reach the server.", issues: [] };
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      {animation.status === "loading" && <p role="status">Recording a run…</p>}
      {animation.status === "error" && <p role="alert">{animation.message}</p>}
      {animation.status === "ok" && (
        <AnimationView
          key={JSON.stringify(animation.data.input)}
          animation={animation.data}
          python={a.python_code}
          cpp={a.cpp_code}
        />
      )}
      {inputs.length > 0 && (
        <InputEditor params={inputs} initial={shown} defaults={defaults} running={running} onRun={run} />
      )}
    </div>
  );
}

defmodule BrazilianSoccer.Model do
  @moduledoc """
  Node structs of the knowledge graph: `Competition`, `Team`, `Match`, `Player`.

  Edges are kept as ids on the nodes (a match points at two team ids, a player
  points at the team id of its club) plus the adjacency indexes built in
  `BrazilianSoccer.Data.Graph`.
  """

  defmodule Competition do
    @moduledoc "A competition node (Série A/B/C, Copa do Brasil, Libertadores)."
    @enforce_keys [:id, :name]
    defstruct [:id, :name, :short_name, :type, :country]

    @type t :: %__MODULE__{
            id: atom,
            name: String.t(),
            short_name: String.t(),
            type: :league | :cup,
            country: String.t()
          }
  end

  defmodule Team do
    @moduledoc "A club node, with every raw spelling that mapped onto it."
    @enforce_keys [:id, :name]
    defstruct [
      :id,
      :name,
      :state,
      :state_name,
      :country,
      aliases: [],
      match_count: 0,
      competitions: [],
      seasons: [],
      player_ids: []
    ]

    @type t :: %__MODULE__{}
  end

  defmodule Match do
    @moduledoc "A match edge between two team nodes."
    @enforce_keys [:id, :competition, :home_id, :away_id]
    defstruct [
      :id,
      :competition,
      :season,
      :round,
      :stage,
      :date,
      :time,
      :home_id,
      :away_id,
      :home_name,
      :away_name,
      :home_state,
      :away_state,
      :home_goals,
      :away_goals,
      :venue,
      sources: [],
      stats: %{}
    ]

    @type t :: %__MODULE__{}

    @doc "`:home_win | :away_win | :draw | :unknown`"
    def result(%__MODULE__{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a) do
      cond do
        h > a -> :home_win
        h < a -> :away_win
        true -> :draw
      end
    end

    def result(%__MODULE__{}), do: :unknown

    @doc "Result from the point of view of `team_id`: `:win | :draw | :loss | :unknown`."
    def outcome_for(%__MODULE__{} = match, team_id) do
      case {result(match), side(match, team_id)} do
        {:unknown, _} -> :unknown
        {_, nil} -> :unknown
        {:draw, _} -> :draw
        {:home_win, :home} -> :win
        {:home_win, :away} -> :loss
        {:away_win, :away} -> :win
        {:away_win, :home} -> :loss
      end
    end

    @doc "`:home`, `:away` or `nil`."
    def side(%__MODULE__{home_id: id}, id), do: :home
    def side(%__MODULE__{away_id: id}, id), do: :away
    def side(%__MODULE__{}, _), do: nil

    @doc "Goals scored / conceded by `team_id`."
    def goals_for(%__MODULE__{} = match, team_id) do
      case side(match, team_id) do
        :home -> match.home_goals
        :away -> match.away_goals
        nil -> nil
      end
    end

    def goals_against(%__MODULE__{} = match, team_id) do
      case side(match, team_id) do
        :home -> match.away_goals
        :away -> match.home_goals
        nil -> nil
      end
    end

    def total_goals(%__MODULE__{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a),
      do: h + a

    def total_goals(%__MODULE__{}), do: nil

    def played?(%__MODULE__{home_goals: h, away_goals: a}), do: is_integer(h) and is_integer(a)

    @doc "Goal margin (absolute)."
    def margin(%__MODULE__{home_goals: h, away_goals: a}) when is_integer(h) and is_integer(a),
      do: abs(h - a)

    def margin(%__MODULE__{}), do: nil
  end

  defmodule Player do
    @moduledoc "A player node from the FIFA database."
    @enforce_keys [:id, :name]
    defstruct [
      :id,
      :name,
      :age,
      :nationality,
      :overall,
      :potential,
      :club,
      :club_id,
      :position,
      :jersey_number,
      :height,
      :weight,
      :value,
      :value_eur,
      :wage,
      :preferred_foot,
      :work_rate,
      :joined,
      :contract_until,
      skills: %{}
    ]

    @type t :: %__MODULE__{}

    @forwards ~w(ST CF LW RW LS RS LF RF)
    @midfielders ~w(CM CAM CDM LM RM LCM RCM LDM RDM LAM RAM)
    @defenders ~w(CB LB RB LWB RWB LCB RCB)

    @doc "Coarse position group for a FIFA position code."
    def position_group(%__MODULE__{position: pos}), do: position_group(pos)
    def position_group(pos) when pos in @forwards, do: :forward
    def position_group(pos) when pos in @midfielders, do: :midfielder
    def position_group(pos) when pos in @defenders, do: :defender
    def position_group("GK"), do: :goalkeeper
    def position_group(_), do: :unknown
  end
end

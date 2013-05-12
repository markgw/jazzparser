(* Minimal version of tspath, without test code and printing utils *)
open List;;

type cadence = Point of int * int 
             | Leftonto of cadence
             | Rightonto of cadence
             | Coord of cadence list * cadence
             | CoordRes;;
type lf = cadence list;;

(* Some utilities for the algorithm *)
type nearest = Nearest of ((int * int) list) * nearest
             | End;;
let addrp (x1,y1) (x2,y2) = (x1+x2, y1+y2);;
let butlast lst = rev (tl (rev lst))

(********* The algorithm **********)
let rec get_cad_path cad coordres = 
    match cad with 
    | Leftonto res -> 
            (* Process resolution first, then prepend a left step *)
            let respath = (get_cad_path res coordres) in
                (addrp (-1,0) (hd respath))::respath
    | Rightonto res -> 
            (* Process resolution first, then prepend a right step *)
            let respath = (get_cad_path res coordres) in
                (addrp (1,0) (hd respath))::respath
    | Point (x,y) -> 
            (* Just use this point for now: it is still subject to shfiting 
                by the "nearest" operator at the top level *)
            [(x,y)]
    | Coord (pcads, res) -> 
            (* First get the path for the shared resolution *)
            let respath = (get_cad_path res coordres) in
                (* Get the path for each partial cadence, resolving to the 
                    start of the shared resolution, remove the final point 
                    (the resolution) and concatenate them all
                *)
                (fold_left 
                    (fun base cad -> (butlast 
                            (get_cad_path cad (hd respath))) @ base) 
                        [] (rev pcads)) 
                    @ respath
    | CoordRes -> 
            (* Should only occur within a coordination. Use the resolution 
                point we've been given. It should get removed later after 
                the cadence has been processed relative to it *)
            [coordres]
;;

(* Pass in (0,0) as the cadence resolution. If the LF is well-formed, 
    this will never be used. *)
let cadence_path cad = get_cad_path cad (0,0);;

(* Process each cadence in turn, linking them with the "nearest" operator *)
let rec get_path lform =
    match lform with
      [] -> End
    | cad::cads -> Nearest ((cadence_path cad), (get_path cads));;

(* I've not implemented the transformation performed by "nearest", because 
    it's kind of messy and not very interesting. It would look something like 
    this: *)
let nearest_to path base = 
    (* Return the path, shifted to an equal-temperament equivalent 
        such that its end point is as close as possible to base.
        Not implemented here. *)
    path
;;
let rec flatten_nearest lst =
    match lst with
      End -> [] (* Only happens for empty piece *)
    | Nearest (path1, End) -> nearest_to path1 (0,0)
    | Nearest (path1, morepaths) -> 
        let path2 = (flatten_nearest morepaths) in 
            (nearest_to path1 (hd path2)) @ path2
;;

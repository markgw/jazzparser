open List;;
open Printf;;

type cadence = Point of int * int 
             | Leftonto of cadence
             | Rightonto of cadence
             | Coord of cadence list * cadence
             | CoordRes;;
type lf = cadence list;;

exception Empty_cadence

(* Printing of these datatypes *)
let rec print_cad cad = 
    match cad with
      Leftonto res -> print_string "leftonto("; print_cad res; print_string ")"
    | Rightonto res -> print_string "rightonto("; print_cad res; print_string ")"
    | Point (x,y) -> printf "<%d,%d>" x y
    | Coord ((crd::[]), res) -> print_cad crd; print_string ")"; print_cad res
    | Coord ((crd::crds), res) -> print_string "("; print_cad crd; 
                            print_string " & "; print_cad (Coord (crds, res))
    | Coord ([], res) -> raise Empty_cadence
    | CoordRes -> print_string "x"
;;
let rec print_lf_inner lform = 
    match lform with
      [] -> ()
    | cad::[] -> print_cad cad
    | cad::cads -> print_cad cad; print_string ", "; print_lf_inner cads
let print_lf lform = 
    print_string "["; print_lf_inner lform; print_string "]"


(* Define some (partial and full) logical forms to test on *)
let test1 = Leftonto (Point (0,0));;
let test2 = Coord (((Leftonto CoordRes)::(Leftonto (Leftonto CoordRes))::[]), 
                        (Point (0,0)));;
let lf1 = [test1; test2];;
(* Print out all the examples *)
print_cad test1;;
print_string "\n";;
print_cad test2;;
print_string "\n";;
print_lf lf1;;
print_string "\n";;


(* Some utilities for the algorithm *)
type nearest = Nearest of ((int * int) list) * nearest
             | End;;
let addrp (x1,y1) (x2,y2) = (x1+x2, y1+y2);;
let butlast lst = rev (tl (rev lst))

(* Printing *)
let int_sign i = if i>=0 then "+" else "-";;
let print_rpoint (x,y) = printf "(x%s%d, y%s%d)" (int_sign x) (abs x) (int_sign y) (abs y);;
let print_point (x,y) = printf "(%d, %d)" x y;;
let rec print_rpoint_list rplist = 
    match rplist with
      [] -> ()
    | l::[] -> print_rpoint l
    | l::ls -> print_rpoint l; print_string ","; print_rpoint_list ls
let rec print_path path = 
    match path with 
      Nearest (a, End) -> print_rpoint_list a
    | Nearest (a, b) -> print_rpoint_list a; print_string " ~nearest~ "; print_path b
    | End -> ();;
let rec print_point_list plist =
    match plist with
      [] -> ()
    | p::[] -> print_point p
    | p::ps -> print_point p; print_string ", "; print_point_list ps
;;


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


(* Try getting a path for the logical form *)
let path1 = get_path lf1;;
print_path path1;;
print_string "\n";;
(* This returns dummy output for now: the paths don't get shifted.
    It so happens that this is the correct output for the example! *)
let finalpath = flatten_nearest path1;;
print_point_list finalpath;;
print_string "\n";;
